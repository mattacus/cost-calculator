"""Helpers for building synthetic datacenter load profiles."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable

import pandas as pd

from ai_datacenter_synthetic_load_profile_generator import SyntheticAILoadGenerator


SCENARIO_NAMES: Dict[str, str] = {
    "A": "Heavy Training",
    "B": "Inference-Dominant",
    "C": "Mixed Workload",
    "D": "Flat High",
}


@dataclass(frozen=True)
class LoadProfileConfig:
    nameplate_mw: float
    scenario: str = "B"
    start_date: str = "2026-01-01"
    location: str = "southwest"
    noise_std: float = 0.02
    random_seed: int = 42


def _project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def build_synthetic_load_profile(config: LoadProfileConfig) -> pd.DataFrame:
    """Build a single synthetic load profile using the base scenario rules."""
    generator = SyntheticAILoadGenerator(
        nameplate_mw=config.nameplate_mw,
        base_dir=_project_root(),
    )

    scenario = config.scenario.upper()
    if scenario == "D":
        method = "simple"
        return generator.generate_annual_profile(
            scenario=scenario,
            method=method,
            start_date=config.start_date,
            location=config.location,
            random_seed=config.random_seed,
        )

    method = "stochastic"
    return generator.generate_annual_profile(
        scenario=scenario,
        method=method,
        start_date=config.start_date,
        location=config.location,
        noise_std=config.noise_std,
        random_seed=config.random_seed,
    )


def build_all_scenarios(
    nameplate_mw: float,
    scenarios: Iterable[str] = ("A", "B", "C", "D"),
    start_date: str = "2026-01-01",
    location: str = "southwest",
    noise_std: float = 0.02,
    random_seed: int = 42,
) -> Dict[str, pd.DataFrame]:
    """Generate profiles for multiple scenarios using base rules."""
    generator = SyntheticAILoadGenerator(
        nameplate_mw=nameplate_mw,
        base_dir=_project_root(),
    )
    profiles: Dict[str, pd.DataFrame] = {}

    for scenario in scenarios:
        scenario_key = scenario.upper()
        if scenario_key == "D":
            method = "simple"
            profiles[scenario_key] = generator.generate_annual_profile(
                scenario=scenario_key,
                method=method,
                start_date=start_date,
                location=location,
                random_seed=random_seed,
            )
        else:
            method = "stochastic"
            profiles[scenario_key] = generator.generate_annual_profile(
                scenario=scenario_key,
                method=method,
                start_date=start_date,
                location=location,
                noise_std=noise_std,
                random_seed=random_seed,
            )

    return profiles
