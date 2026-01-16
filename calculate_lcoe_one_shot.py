#!/usr/bin/env python3
"""Command line wrapper for LCOE calculation."""

import argparse
import logging
from core.datacenter import DataCenter
from core.powerflow_model import get_solar_ac_dataframe, simulate_system
from core.defaults import BESS_HRS_STORAGE

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='Calculate LCOE for a single datacenter configuration')

    # Required arguments
    parser.add_argument('--lat', type=float, required=True,
                        help='Latitude of the datacenter')
    parser.add_argument('--long', type=float, required=True,
                        help='Longitude of the datacenter')
    parser.add_argument('--solar-mw', type=int, required=True, dest='solar_pv_capacity_mw',
                        help='Solar PV capacity in MW')
    parser.add_argument('--bess-mw', type=int, required=True, dest='bess_max_power_mw',
                        help='BESS power capacity in MW')
    parser.add_argument('--bess-mwh', type=float, dest='bess_capacity_mwh',
                        help='BESS energy capacity in MWh')
    parser.add_argument('--generator-mw', type=int, required=True, dest='generator_capacity_mw',
                        help='Generator capacity in MW')
    parser.add_argument('--datacenter-load-mw', type=int,
                        help='Datacenter load in MW')

    # Optional arguments (all parameter names match DataCenter class)
    parser.add_argument('--generator-type', choices=['Gas Engine', 'Gas Turbine'],
                        help='Type of generator')
    parser.add_argument('--bess-hrs-storage', type=int,
                        help='BESS hours of storage (used if --bess-mwh not provided)')
    parser.add_argument('--solar-capex-total-dollar-per-w', type=float,
                        help='Solar CAPEX in $/W')
    parser.add_argument('--bess-capex-total-dollar-per-kwh', type=float,
                        help='BESS CAPEX in $/kWh')
    parser.add_argument('--generator-capex-total-dollar-per-kw', type=float,
                        help='Generator CAPEX in $/kW')
    parser.add_argument('--system-integration-capex-total-dollar-per-kw', type=float,
                        help='System integration CAPEX in $/kW')
    parser.add_argument('--soft-costs-capex-total-pct', type=float,
                        help='Soft costs CAPEX as percentage')
    parser.add_argument('--fuel-price-dollar-per-mmbtu', type=float,
                        help='Fuel price in $/MMBtu')
    parser.add_argument('--fuel-escalator-pct', type=float,
                        help='Fuel price escalator in % per year')
    parser.add_argument('--om-solar-fixed-dollar-per-kw', type=float,
                        help='Solar fixed O&M in $/kW')
    parser.add_argument('--om-bess-fixed-dollar-per-kw', type=float,
                        help='BESS fixed O&M in $/kW')
    parser.add_argument('--om-generator-fixed-dollar-per-kw', type=float,
                        help='Generator fixed O&M in $/kW')
    parser.add_argument('--om-generator-variable-dollar-per-kwh', type=float,
                        help='Generator variable O&M in $/kWh')
    parser.add_argument('--om-bos-fixed-dollar-per-kw-load', type=float,
                        help='Balance of system fixed O&M in $/kW-load')
    parser.add_argument('--om-soft-pct', type=float,
                        help='Soft O&M as percentage of hard costs')
    parser.add_argument('--om-escalator-pct', type=float,
                        help='O&M escalator in % per year')
    parser.add_argument('--investment-tax-credit-pct', type=float,
                        help='Investment tax credit percentage')
    parser.add_argument('--cost-of-debt-pct', type=float,
                        help='Cost of debt percentage')
    parser.add_argument('--leverage-pct', type=float,
                        help='Debt leverage percentage')
    parser.add_argument('--debt-term-years', type=int,
                        help='Debt term in years')
    parser.add_argument('--cost-of-equity-pct', type=float,
                        help='Cost of equity percentage')
    parser.add_argument('--combined-tax-rate-pct', type=float,
                        help='Combined tax rate percentage')
    parser.add_argument('--construction-time-years', type=int,
                        help='Construction time in years')
    parser.add_argument('--depreciation-schedule', type=float, nargs='+',
                        help='Depreciation schedule (space-separated list of percentages)')

    return vars(parser.parse_args())


if __name__ == '__main__':
    args = parse_args()

    if args.get('bess_capacity_mwh') is None:
        bess_hours = args.get('bess_hrs_storage', BESS_HRS_STORAGE)
        args['bess_capacity_mwh'] = args['bess_max_power_mw'] * bess_hours

    # Remove None values from args
    inputs = {k: v for k, v in args.items() if v is not None and k not in [
        'lat', 'long']}

    logger.info(
        f"Getting solar generation data for ({args['lat']}, {args['long']})")
    solar_ac_dataframe = get_solar_ac_dataframe(args['lat'], args['long'])

    logger.info(
        f"Simulating battery and solar powerflow for ({args['lat']}, {args['long']})")
    powerflow_results = simulate_system(
        args['lat'],
        args['long'],
        solar_ac_dataframe,
        inputs['solar_pv_capacity_mw'],
        inputs['bess_max_power_mw'],
        inputs['generator_capacity_mw'],
        inputs['datacenter_load_mw'],
        inputs['bess_capacity_mwh'],
    )

    logger.info("Creating DataCenter instance and calculating LCOE...")
    data_center = DataCenter(
        **inputs, filtered_simulation_data=powerflow_results['annual_results'])
    lcoe, proforma = data_center.calculate_lcoe()

    logger.info(
        f"Results for ({args['lat']}, {args['long']}) for {inputs['solar_pv_capacity_mw']}MW solar | "
        f"{inputs['bess_max_power_mw']}MW / {inputs['bess_capacity_mwh']}MWh BESS | "
        f"{inputs['generator_capacity_mw']}MW generator"
    )
    logger.info(f"LCOE: ${lcoe:.2f}/MWh")
