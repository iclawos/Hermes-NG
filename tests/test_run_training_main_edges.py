"""run_training.main() 边界覆盖。

覆盖：config 缺失报错、resume 恢复路径。
"""

import asyncio
from pathlib import Path

import pytest
import yaml


def _write_cfg(tmp_path: Path, **training) -> Path:
    cfg = {"training": {
        "algorithm": "CISPO",
        "num_epochs": 1,
        "batch_size": 4,
        "log_dir": str(tmp_path),
        **training,
    }}
    p = tmp_path / "cfg.yaml"
    p.write_text(yaml.safe_dump(cfg))
    return p


class TestMainEdgeCases:
    def test_main_missing_config(self, tmp_path):
        from zilli.run_training import main

        with pytest.raises(FileNotFoundError, match="Config not found"):
            asyncio.run(main(str(tmp_path / "missing.yaml")))

    def test_main_resume_from_checkpoint(self, tmp_path):
        from zilli.run_training import main

        cfg_path = _write_cfg(tmp_path, num_epochs=1)
        # 先跑一轮，产出 final checkpoint
        exp = asyncio.run(main(str(cfg_path), "resume_test"))
        assert exp.summary()["epochs"] >= 1
        ckpt = list(tmp_path.glob("resume_test_ckpt_final.json"))
        assert ckpt

        # 用 resume 路径再跑一次（跳过训练，直接恢复到 checkpoint）
        exp2 = asyncio.run(main(str(cfg_path), "resume_test",
                                resume=str(ckpt[0])))
        # resume 后 log 了一条 resumed 记录
        assert exp2.metrics and exp2.metrics[-1].get("resumed") is True

    def test_main_resume_nonexistent_checkpoint(self, tmp_path):
        from zilli.run_training import main

        cfg_path = _write_cfg(tmp_path, num_epochs=1)
        with pytest.raises(FileNotFoundError):
            asyncio.run(main(str(cfg_path), "x",
                             resume=str(tmp_path / "nope.json")))
