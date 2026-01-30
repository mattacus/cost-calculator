"""Run a full-year (TMY) curtailment report for a hybrid system."""

from core.powerflow_model import (
    get_solar_ac_dataframe,
    scale_solar_generation,
    simulate_battery_operation,
)
from core.defaults import DATACENTER_DEMAND_MW
from core.load_profiles import LoadProfileConfig, build_synthetic_load_profile


def run_full_year_curtailment_report() -> None:
    # Location: Monahans, Texas (US)
    lat, lon = 31.59, -102.89

    # System configuration
    solar_capacity_mw = 200
    battery_power_mw = 100
    battery_capacity_mwh = 200
    generator_capacity_mw = 125
    datacenter_load_mw = DATACENTER_DEMAND_MW
    load_profile_scenario = "C"

    # Initial battery state of charge (MWh). Using 0 avoids immediate curtailment
    # from starting the year with a full battery.
    initial_battery_charge_mwh = 0

    # Full-year TMY simulation (year 1)
    operating_year = 1

    solar_df = get_solar_ac_dataframe(lat, lon)
    scaled_df = scale_solar_generation(
        solar_df.copy(), solar_capacity_mw, operating_year)

    load_profile_df = build_synthetic_load_profile(
        LoadProfileConfig(
            nameplate_mw=datacenter_load_mw,
            scenario=load_profile_scenario,
        )
    )

    hourly = simulate_battery_operation(
        scaled_df,
        battery_capacity_mwh,
        battery_power_mw,
        initial_battery_charge=initial_battery_charge_mwh,
        generator_capacity=generator_capacity_mw,
        # load_mw=datacenter_load_mw,  # static load profile
        load_mw=load_profile_df["load_mw"].to_numpy(),  # dynamic load profile
        operating_year=operating_year,
    )

    # Curtailment report
    total_hours = len(hourly)
    curtailed_hours = int((hourly["curtailed_solar_mwh"] > 0).sum())
    curtailed_mwh = float(hourly["curtailed_solar_mwh"].sum())
    percent_hours_curtailed = (curtailed_hours / total_hours) * 100

    # Diagnostic breakdown: power-limited vs full-battery curtailment
    battery_full_hours = int(
        (
            (hourly["curtailed_solar_mwh"] > 0)
            & (hourly["battery_state_mwh"] >= battery_capacity_mwh - 1e-6)
        ).sum()
    )
    power_limited_hours = curtailed_hours - battery_full_hours

    excess_solar_hours = int(
        (hourly["scaled_solar_generation_mw"] > hourly["load_mw"]).sum()
    )

    print("Curtailment report (full year TMY)")
    print(f"Total hours: {total_hours}")
    print(
        f"Curtailed hours: {curtailed_hours} ({percent_hours_curtailed:.2f}%)")
    print(f"Total curtailed energy: {curtailed_mwh:,.2f} MWh")
    print(f"Hours with excess solar (solar > load): {excess_solar_hours}")
    print(f"Curtailment while battery full: {battery_full_hours}")
    print(
        f"Curtailment while battery not full (power-limited): {power_limited_hours}")


if __name__ == "__main__":
    run_full_year_curtailment_report()
