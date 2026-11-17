from __future__ import annotations

import math
from typing import Any

import torch
import torch.nn as nn
import torch.nn.functional as F


ALPHABET = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ +-*/=().,:?%<>\n"


class CharTokenizer:
    def __init__(self, alphabet: str = ALPHABET) -> None:
        if not alphabet or len(set(alphabet)) != len(alphabet):
            raise ValueError("Alphabet must be non-empty and contain unique characters")
        self.alphabet = alphabet
        self.stoi = {character: index for index, character in enumerate(alphabet)}
        self.itos = tuple(alphabet)

    @property
    def vocab_size(self) -> int:
        return len(self.alphabet)

    def encode(self, text: str) -> list[int]:
        unknown = sorted(set(text).difference(self.stoi))
        if unknown:
            raise ValueError(f"Text contains unsupported characters: {unknown}")
        return [self.stoi[character] for character in text]

    def decode(self, token_ids: Any) -> str:
        if hasattr(token_ids, "tolist"):
            token_ids = token_ids.tolist()
        if token_ids and isinstance(token_ids[0], list):
            return "".join(self.itos[int(item)] for row in token_ids for item in row)
        return "".join(self.itos[int(item)] for item in token_ids)


class CausalSelfAttention(nn.Module):
    def __init__(self, dimension: int, heads: int, context_length: int, dropout: float) -> None:
        super().__init__()
        if dimension % heads:
            raise ValueError("Embedding dimension must be divisible by attention heads")
        self.heads = heads
        self.head_dimension = dimension // heads
        self.qkv = nn.Linear(dimension, 3 * dimension)
        self.projection = nn.Linear(dimension, dimension)
        self.attention_dropout = nn.Dropout(dropout)
        self.residual_dropout = nn.Dropout(dropout)
        mask = torch.tril(torch.ones(context_length, context_length, dtype=torch.bool))
        self.register_buffer("causal_mask", mask, persistent=False)

    def forward(self, hidden: torch.Tensor) -> torch.Tensor:
        batch, sequence, dimension = hidden.shape
        if sequence > self.causal_mask.shape[0]:
            raise ValueError("Input sequence exceeds configured context length")
        query, key, value = self.qkv(hidden).chunk(3, dim=-1)
        query = query.view(batch, sequence, self.heads, self.head_dimension).transpose(1, 2)
        key = key.view(batch, sequence, self.heads, self.head_dimension).transpose(1, 2)
        value = value.view(batch, sequence, self.heads, self.head_dimension).transpose(1, 2)
        scores = query @ key.transpose(-2, -1) / math.sqrt(self.head_dimension)
        mask = self.causal_mask[:sequence, :sequence]
        scores = scores.masked_fill(~mask, torch.finfo(scores.dtype).min)
        weights = F.softmax(scores, dim=-1)
        weights = self.attention_dropout(weights)
        attended = weights @ value
        attended = attended.transpose(1, 2).contiguous().view(batch, sequence, dimension)
        return self.residual_dropout(self.projection(attended))


class TransformerBlock(nn.Module):
    def __init__(self, dimension: int, heads: int, context_length: int, dropout: float, multiplier: int) -> None:
        super().__init__()
        self.norm_attention = nn.LayerNorm(dimension)
        self.attention = CausalSelfAttention(dimension, heads, context_length, dropout)
        self.norm_feedforward = nn.LayerNorm(dimension)
        self.feedforward = nn.Sequential(
            nn.Linear(dimension, multiplier * dimension),
            nn.GELU(),
            nn.Linear(multiplier * dimension, dimension),
            nn.Dropout(dropout),
        )

    def forward(self, hidden: torch.Tensor) -> torch.Tensor:
        hidden = hidden + self.attention(self.norm_attention(hidden))
        hidden = hidden + self.feedforward(self.norm_feedforward(hidden))
        return hidden


class ULTRONTransformer(nn.Module):
    def __init__(
        self,
        vocab_size: int = len(ALPHABET),
        context_length: int = 192,
        dimension: int = 256,
        layers: int = 5,
        heads: int = 8,
        feedforward_multiplier: int = 4,
        dropout: float = 0.1,
    ) -> None:
        super().__init__()
        if vocab_size < 2 or context_length < 2 or dimension < 8 or layers < 1 or heads < 1:
            raise ValueError("Model dimensions must be positive and large enough")
        if dimension % heads:
            raise ValueError("Embedding dimension must be divisible by attention heads")
        if feedforward_multiplier < 1 or not 0.0 <= dropout < 1.0:
            raise ValueError("Invalid feedforward multiplier or dropout")
        self.vocab_size = vocab_size
        self.context_length = context_length
        self.dimension = dimension
        self.layers = layers
        self.heads = heads
        self.feedforward_multiplier = feedforward_multiplier
        self.token_embedding = nn.Embedding(vocab_size, dimension)
        self.position_embedding = nn.Embedding(context_length, dimension)
        self.blocks = nn.ModuleList(
            TransformerBlock(dimension, heads, context_length, dropout, feedforward_multiplier)
            for _ in range(layers)
        )
        self.final_norm = nn.LayerNorm(dimension)
        self.language_head = nn.Linear(dimension, vocab_size)
        self.apply(self._initialize_parameters)

    @staticmethod
    def _initialize_parameters(module: nn.Module) -> None:
        if isinstance(module, (nn.Linear, nn.Embedding)):
            nn.init.normal_(module.weight, mean=0.0, std=0.02)
            if isinstance(module, nn.Linear) and module.bias is not None:
                nn.init.zeros_(module.bias)
        elif isinstance(module, nn.LayerNorm):
            nn.init.ones_(module.weight)
            nn.init.zeros_(module.bias)

    def forward(
        self,
        token_ids: torch.Tensor,
        targets: torch.Tensor | None = None,
    ) -> tuple[torch.Tensor, torch.Tensor | None]:
        if token_ids.ndim != 2:
            raise ValueError("Token input must have shape [batch, sequence]")
        batch, sequence = token_ids.shape
        if sequence > self.context_length:
            raise ValueError("Input sequence exceeds configured context length")
        if token_ids.numel() and (token_ids.min() < 0 or token_ids.max() >= self.vocab_size):
            raise ValueError("Token ID is outside the configured vocabulary")
        positions = torch.arange(sequence, device=token_ids.device)
        hidden = self.token_embedding(token_ids) + self.position_embedding(positions)[None, :, :]
        for block in self.blocks:
            hidden = block(hidden)
        logits = self.language_head(self.final_norm(hidden))
        loss = None
        if targets is not None:
            if targets.shape != token_ids.shape:
                raise ValueError("Targets must have the same shape as token input")
            loss = F.cross_entropy(logits.reshape(batch * sequence, self.vocab_size), targets.reshape(batch * sequence))
        return logits, loss

    def parameter_count(self) -> int:
        return sum(parameter.numel() for parameter in self.parameters() if parameter.requires_grad)

    def architecture(self) -> dict[str, int | float | str]:
        return {
            "type": "decoder_only_transformer",
            "tokenizer": "character",
            "vocab_size": self.vocab_size,
            "context_length": self.context_length,
            "dimension": self.dimension,
            "layers": self.layers,
            "heads": self.heads,
            "feedforward_multiplier": self.feedforward_multiplier,
            "parameters": self.parameter_count(),
            "initialization": "random_normal",
        }
