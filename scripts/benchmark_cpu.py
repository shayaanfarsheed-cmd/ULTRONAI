from __future__ import annotations
import argparse, json, os, platform, resource, statistics, sys, time
from pathlib import Path

# Executing `python scripts/benchmark_cpu.py` puts scripts/ on sys.path,
# not necessarily the repository root where ULTRON's modules live.
REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

import torch
from ultron_model import CharTokenizer, ULTRONTransformer
from ultron_training import train_one_batch

def run_case(threads: int, foreach: bool, steps: int, warmup: int) -> dict:
    torch.set_num_threads(threads)
    try: torch.set_num_interop_threads(1)
    except RuntimeError: pass
    torch.manual_seed(20261119)
    tokenizer = CharTokenizer()
    model = ULTRONTransformer(vocab_size=tokenizer.vocab_size)
    optimizer = torch.optim.AdamW(model.parameters(), lr=0.0003, foreach=foreach)
    inputs = torch.randint(0, tokenizer.vocab_size, (2, 64))
    batch = {"input_ids": inputs, "labels": inputs.clone()}
    for _ in range(warmup): train_one_batch(model, optimizer, batch, "cpu")
    durations=[]
    for _ in range(steps):
        start=time.perf_counter()
        loss=train_one_batch(model, optimizer, batch, "cpu")
        durations.append(time.perf_counter()-start)
        if not torch.isfinite(torch.tensor(loss)): raise RuntimeError("Non-finite benchmark loss")
    return {"threads":threads,"foreach":foreach,"steps":steps,"steps_per_second":steps/sum(durations),
            "median_step_seconds":statistics.median(durations),"peak_rss_mb":resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024}

def main():
    parser=argparse.ArgumentParser(description="Bounded synthetic CPU benchmark; never starts production training.")
    parser.add_argument("--steps",type=int,default=4); parser.add_argument("--warmup",type=int,default=1)
    args=parser.parse_args()
    if not 1<=args.steps<=20 or not 0<=args.warmup<=5: parser.error("steps 1..20; warmup 0..5")
    results=[run_case(t,f,args.steps,args.warmup) for t in (1,2) for f in (False,True)]
    print(json.dumps({"benchmark":"synthetic_cpu_step_throughput","production_training_started":False,
      "platform":platform.platform(),"logical_cpus":os.cpu_count(),"torch_version":torch.__version__,"results":results},indent=2))
if __name__=="__main__": main()
