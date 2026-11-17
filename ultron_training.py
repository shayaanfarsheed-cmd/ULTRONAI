from __future__ import annotations

import random
import re
from collections import defaultdict
from contextlib import nullcontext
from typing import Any, Callable, Mapping, Sequence

import torch
from torch.utils.data import Dataset


def format_example(example: Mapping[str, Any]) -> tuple[str, str]:
    prefix = f"Question: {example['question']}\nSolution:\n"
    completion = "\n".join(example["steps"]) + f"\nAnswer: {example['answer']}\n"
    return prefix, completion


def encode_example(example: Mapping[str, Any], tokenizer: Any, context_length: int) -> dict[str, list[int]]:
    prefix, completion = format_example(example)
    prefix_ids = tokenizer.encode(prefix)
    token_ids = tokenizer.encode(prefix + completion)
    if len(token_ids) < 2:
        raise ValueError("Training example is too short")
    if len(token_ids) - 1 > context_length:
        raise ValueError(f"Training example needs {len(token_ids) - 1} tokens but context is {context_length}")
    input_ids = token_ids[:-1]
    labels = token_ids[1:]
    masked_count = max(0, len(prefix_ids) - 1)
    labels[:masked_count] = [-100] * masked_count
    if all(value == -100 for value in labels):
        raise ValueError("Training example has no target tokens")
    return {"input_ids": input_ids, "labels": labels}


class EncodedMathDataset(Dataset):
    def __init__(self, examples: Sequence[Mapping[str, Any]], tokenizer: Any, context_length: int) -> None:
        if not examples:
            raise ValueError("Training dataset cannot be empty")
        self.examples = [encode_example(example, tokenizer, context_length) for example in examples]

    def __len__(self) -> int:
        return len(self.examples)

    def __getitem__(self, index: int) -> dict[str, list[int]]:
        return self.examples[index]


def collate_math_batch(items: Sequence[Mapping[str, Sequence[int]]], pad_token_id: int = 0) -> dict[str, torch.Tensor]:
    if not items:
        raise ValueError("Cannot collate an empty batch")
    maximum = max(len(item["input_ids"]) for item in items)
    inputs = torch.full((len(items), maximum), int(pad_token_id), dtype=torch.long)
    labels = torch.full((len(items), maximum), -100, dtype=torch.long)
    for index, item in enumerate(items):
        input_values = torch.tensor(item["input_ids"], dtype=torch.long)
        label_values = torch.tensor(item["labels"], dtype=torch.long)
        inputs[index, :input_values.numel()] = input_values
        labels[index, :label_values.numel()] = label_values
    return {"input_ids": inputs, "labels": labels}


class MathBatchStream:
    def __init__(
        self,
        examples: Sequence[Mapping[str, Any]],
        tokenizer: Any,
        context_length: int,
        batch_size: int,
        seed: int,
        shuffle: bool = True,
    ) -> None:
        if batch_size < 1:
            raise ValueError("Batch size must be positive")
        self.dataset = EncodedMathDataset(examples, tokenizer, context_length)
        self.batch_size = batch_size
        self.shuffle = shuffle
        self.rng = random.Random(seed)
        self.order = list(range(len(self.dataset)))
        self.epoch = 0
        self.position = 0
        if self.shuffle:
            self.rng.shuffle(self.order)

    def next_batch(self, pad_token_id: int = 0) -> dict[str, torch.Tensor]:
        if self.position >= len(self.order):
            self.epoch += 1
            self.position = 0
            self.order = list(range(len(self.dataset)))
            if self.shuffle:
                self.rng.shuffle(self.order)
        selected = self.order[self.position:self.position + self.batch_size]
        self.position += len(selected)
        return collate_math_batch([self.dataset[index] for index in selected], pad_token_id)

    def state_dict(self) -> dict[str, Any]:
        return {
            "epoch": self.epoch,
            "position": self.position,
            "order": list(self.order),
            "batch_size": self.batch_size,
            "shuffle": self.shuffle,
            "rng_state": self.rng.getstate(),
        }

    def load_state_dict(self, state: Mapping[str, Any]) -> None:
        order = list(state["order"])
        if sorted(order) != list(range(len(self.dataset))):
            raise ValueError("Saved data order does not match the current dataset")
        if int(state["batch_size"]) != self.batch_size or bool(state["shuffle"]) != self.shuffle:
            raise ValueError("Saved data stream settings do not match")
        position = int(state["position"])
        epoch = int(state["epoch"])
        if position < 0 or position > len(order) or epoch < 0:
            raise ValueError("Saved data stream position is invalid")
        self.epoch = epoch
        self.position = position
        self.order = order
        self.rng.setstate(_to_tuple(state["rng_state"]))


def _to_tuple(value: Any) -> Any:
    if isinstance(value, list):
        return tuple(_to_tuple(item) for item in value)
    return value


def make_grad_scaler(device: str | torch.device, precision: str) -> Any | None:
    resolved = torch.device(device)
    if resolved.type != "cuda" or precision != "fp16":
        return None
    try:
        return torch.amp.GradScaler("cuda")
    except (AttributeError, TypeError):
        return torch.cuda.amp.GradScaler()


def train_one_batch(
    model: torch.nn.Module,
    optimizer: torch.optim.Optimizer,
    batch: Mapping[str, torch.Tensor],
    device: str | torch.device,
    precision: str = "none",
    gradient_clip_norm: float = 1.0,
    scaler: Any | None = None,
) -> float:
    resolved = torch.device(device)
    model.train()
    input_ids = batch["input_ids"].to(resolved)
    labels = batch["labels"].to(resolved)
    optimizer.zero_grad(set_to_none=True)
    use_autocast = resolved.type == "cuda" and precision in {"bf16", "fp16"}
    dtype = torch.bfloat16 if precision == "bf16" else torch.float16
    autocast_context = torch.autocast(device_type="cuda", dtype=dtype) if use_autocast else nullcontext()
    with autocast_context:
        _, loss = model(input_ids, labels)
    if loss is None or not bool(torch.isfinite(loss)):
        raise FloatingPointError("Training loss is missing or non-finite")

    if scaler is not None:
        scaler.scale(loss).backward()
        scaler.unscale_(optimizer)
        torch.nn.utils.clip_grad_norm_(model.parameters(), gradient_clip_norm)
        scaler.step(optimizer)
        scaler.update()
    else:
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), gradient_clip_norm)
        optimizer.step()
    return float(loss.detach().cpu())


def train_steps(
    model: torch.nn.Module,
    optimizer: torch.optim.Optimizer,
    stream: MathBatchStream,
    steps: int,
    device: str | torch.device,
    precision: str = "none",
    gradient_clip_norm: float = 1.0,
    scheduler: Any | None = None,
    scaler: Any | None = None,
    start_step: int = 0,
    on_step: Callable[[int, float, MathBatchStream], None] | None = None,
) -> dict[str, Any]:
    if steps < 1:
        raise ValueError("Training steps must be positive")
    last_loss = None
    model.to(device)
    for offset in range(steps):
        batch = stream.next_batch()
        last_loss = train_one_batch(
            model,
            optimizer,
            batch,
            device,
            precision=precision,
            gradient_clip_norm=gradient_clip_norm,
            scaler=scaler,
        )
        if scheduler is not None:
            scheduler.step()
        current_step = start_step + offset + 1
        if on_step is not None:
            on_step(current_step, last_loss, stream)
    return {
        "step": start_step + steps,
        "last_loss": last_loss,
        "data_position": stream.position,
        "data_epoch": stream.epoch,
    }


@torch.no_grad()
def generate_completion(
    model: torch.nn.Module,
    tokenizer: Any,
    question: str,
    context_length: int,
    device: str | torch.device,
    maximum_new_tokens: int = 128,
) -> str:
    resolved = torch.device(device)
    was_training = model.training
    model.eval()
    try:
        prompt = f"Question: {question}\nSolution:\n"
        token_ids = tokenizer.encode(prompt)
        generated: list[int] = []
        for _ in range(maximum_new_tokens):
            context = token_ids[-context_length:]
            inputs = torch.tensor([context], dtype=torch.long, device=resolved)
            logits, _ = model(inputs)
            next_token = int(torch.argmax(logits[0, -1]).item())
            token_ids.append(next_token)
            generated.append(next_token)
            text = tokenizer.decode(generated)
            if "\nAnswer:" in text and text.endswith("\n"):
                break
        return tokenizer.decode(generated)
    finally:
        model.train(was_training)


@torch.no_grad()
def evaluate_by_topic(
    model: torch.nn.Module,
    examples: Sequence[Mapping[str, Any]],
    tokenizer: Any,
    context_length: int,
    device: str | torch.device,
    maximum_examples_per_topic: int = 20,
) -> dict[str, dict[str, float | int]]:
    groups: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for example in examples:
        if len(groups[str(example["topic"])]) < maximum_examples_per_topic:
            groups[str(example["topic"])].append(example)
    results: dict[str, dict[str, float | int]] = {}
    was_training = model.training
    model.eval()
    try:
        for topic, items in groups.items():
            correct = 0
            for example in items:
                completion = generate_completion(
                    model,
                    tokenizer,
                    str(example["question"]),
                    context_length,
                    device,
                )
                match = re.search(r"(?:^|\n)Answer: ([^\n]+)\n", completion)
                if match and match.group(1).strip() == str(example["answer"]).strip():
                    correct += 1
            total = len(items)
            results[topic] = {
                "correct": correct,
                "total": total,
                "accuracy": correct / total if total else 0.0,
            }
        return results
    finally:
        model.train(was_training)


class CurriculumController:
    def __init__(
        self,
        stages: Sequence[Mapping[str, Any]],
        mastery_accuracy: float = 0.9,
        consecutive_evaluations: int = 3,
        require_held_out: bool = True,
    ) -> None:
        if not stages or any(not stage.get("topics") for stage in stages):
            raise ValueError("Curriculum requires at least one stage with topics")
        if not 0.0 < mastery_accuracy <= 1.0 or consecutive_evaluations < 1:
            raise ValueError("Invalid curriculum mastery settings")
        self.stages = [
            {"name": str(stage["name"]), "topics": [str(topic) for topic in stage["topics"]]}
            for stage in stages
        ]
        self.mastery_accuracy = mastery_accuracy
        self.consecutive_evaluations = consecutive_evaluations
        self.require_held_out = require_held_out
        self.stage_index = 0
        self.mastery_streaks = {topic: 0 for topic in self.current_topics}
        self.mastery_scores: dict[str, float] = {}

    @property
    def current_stage(self) -> str | None:
        if self.is_finished:
            return None
        return self.stages[self.stage_index]["name"]

    @property
    def current_topics(self) -> list[str]:
        if self.is_finished:
            return []
        return list(self.stages[self.stage_index]["topics"])

    @property
    def is_finished(self) -> bool:
        return self.stage_index >= len(self.stages)

    def select_topic(self, step: int) -> str | None:
        topics = self.current_topics
        if not topics:
            return None
        return topics[max(0, step) % len(topics)]

    def record_evaluation(self, metrics: Mapping[str, Any], held_out: bool = True) -> bool:
        if self.is_finished or (self.require_held_out and not held_out):
            return False
        for topic in self.current_topics:
            metric = metrics.get(topic)
            if isinstance(metric, Mapping):
                accuracy = float(metric.get("accuracy", 0.0))
            elif metric is not None:
                accuracy = float(metric)
            else:
                accuracy = 0.0
            self.mastery_scores[topic] = accuracy
            if accuracy >= self.mastery_accuracy:
                self.mastery_streaks[topic] = self.mastery_streaks.get(topic, 0) + 1
            else:
                self.mastery_streaks[topic] = 0

        if all(self.mastery_streaks.get(topic, 0) >= self.consecutive_evaluations for topic in self.current_topics):
            self.stage_index += 1
            if not self.is_finished:
                self.mastery_streaks = {topic: 0 for topic in self.current_topics}
            return True
        return False

    def state_dict(self) -> dict[str, Any]:
        return {
            "stage_index": self.stage_index,
            "mastery_streaks": dict(self.mastery_streaks),
            "mastery_scores": dict(self.mastery_scores),
        }

    def load_state_dict(self, state: Mapping[str, Any]) -> None:
        stage_index = int(state["stage_index"])
        if stage_index < 0 or stage_index > len(self.stages):
            raise ValueError("Saved curriculum stage is invalid")
        self.stage_index = stage_index
        self.mastery_streaks = {str(key): int(value) for key, value in state.get("mastery_streaks", {}).items()}
        self.mastery_scores = {str(key): float(value) for key, value in state.get("mastery_scores", {}).items()}
        if not self.is_finished:
            for topic in self.current_topics:
                self.mastery_streaks.setdefault(topic, 0)
