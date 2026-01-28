"""
Simple synthetic load profile generator for off-grid AI datacenter microgrids
Compatible with off-grid AI calculator hourly resolution
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from pathlib import Path


class SyntheticAILoadGenerator:
    """Generate annual hourly load profiles for AI datacenters"""

    # Define weekend reduction factors
    weekend_factors = {
        'A': 0.95,  # Heavy training: minimal reduction
        'B': 0.70,  # Inference: strong reduction
        'C': 0.85,  # Mixed: moderate reduction
        'D': 1.00   # Flat high load: no reduction
    }

    def __init__(self, nameplate_mw=100, base_dir: str | Path | None = None):
        self.nameplate = nameplate_mw
        self.base_dir = Path(base_dir) if base_dir is not None else Path(
            __file__).resolve().parent
        self.scenarios = {
            'A': self._define_scenario_a(),
            'B': self._define_scenario_b(),
            'C': self._define_scenario_c(),
            'D': self._define_scenario_d()
        }

    def _define_scenario_a(self):
        """Heavy Training scenario definition"""
        df = pd.read_csv(
            self.base_dir / 'ScenarioA_HeavyTraining-Hour-LoadMW-Description.csv')
        return {
            'name': 'Heavy Training',
            'profile': df['Load (%)'].values * self.nameplate / 100.0,
            'weekend_factor': self.weekend_factors['A'],
            'description': 'Dedicated training cluster, 75% avg utilization'
        }

    def _define_scenario_b(self):
        """Inference-Dominant scenario definition"""
        df = pd.read_csv(
            self.base_dir / 'ScenarioB_InferenceDominant-Hour-LoadMW-Description.csv')
        return {
            'name': 'Inference-Dominant',
            'profile': df['Load (%)'].values * self.nameplate / 100.0,
            'weekend_factor': self.weekend_factors['B'],
            'description': 'User-facing services, 50% avg utilization, strong diurnal'
        }

    def _define_scenario_c(self):
        """Mixed Workload scenario definition"""
        df = pd.read_csv(
            self.base_dir / 'ScenarioC_MixedWorkload-Hour-LoadMW-Description.csv')
        return {
            'name': 'Mixed Workload',
            'profile': df['Load (%)'].values * self.nameplate / 100.0,
            'weekend_factor': self.weekend_factors['C'],
            'description': 'Training + inference mix, 60% avg utilization'
        }

    def _define_scenario_d(self):
        """Flat/Constant High Load scenario definition"""
        df = pd.read_csv(
            self.base_dir / 'ScenarioD_HighLoadFlat-Activity-Hour-LoadMW-Description.csv')
        return {
            'name': 'Flat High',
            'profile': df['Load (%)'].values * self.nameplate / 100.0,
            'weekend_factor': self.weekend_factors['D'],
            'description': 'Flat high load, constant 85% utilization'
        }

    def generate_annual_profile(self, scenario='B', method='seasonal',
                                start_date='2026-01-01', location='southwest',
                                noise_std=0.02, random_seed=None):
        """
        Generate annual hourly load profile

        Parameters:
        -----------
        scenario : str
            'A', 'B', 'C', or 'D'
        method : str
            'simple' - pure repetition
            'weekend' - weekday/weekend differentiation
            'seasonal' - seasonal + weekend
            'stochastic' - seasonal + weekend + noise
        start_date : str
            Start date in 'YYYY-MM-DD' format
        location : str
            'southwest' or 'moderate' (affects seasonal multipliers)
        noise_std : float
            Standard deviation for stochastic variation (method='stochastic')
        random_seed : int
            Random seed for reproducibility
        """
        if random_seed is not None:
            np.random.seed(random_seed)

        # Get base 24-hour profile
        daily_profile = self.scenarios[scenario]['profile']
        weekend_factor = self.scenarios[scenario]['weekend_factor']

        # Parse start date
        start = datetime.strptime(start_date, '%Y-%m-%d')
        start_day_of_week = start.weekday()  # Monday=0, Sunday=6

        # Generate based on method
        if method == 'simple':
            annual = self._extend_simple(daily_profile)
        elif method == 'weekend':
            annual = self._extend_weekend(
                daily_profile, weekend_factor, start_day_of_week)
        elif method == 'seasonal':
            annual = self._extend_seasonal(daily_profile, weekend_factor,
                                           start_day_of_week, location)
        elif method == 'stochastic':
            annual = self._extend_stochastic(daily_profile, weekend_factor,
                                             start_day_of_week, location, noise_std)
        else:
            raise ValueError(f"Unknown method: {method}")

        # Create datetime index
        timestamps = [start + timedelta(hours=i) for i in range(len(annual))]

        # Return as DataFrame
        df = pd.DataFrame({
            'timestamp': timestamps,
            'load_mw': annual
        })

        return df

    def _extend_simple(self, daily_profile, days=365):
        """Method 1: Pure repetition"""
        return np.tile(daily_profile, days)

    def _extend_weekend(self, daily_profile, weekend_factor, start_dow, days=365):
        """Method 2: Weekend differentiation"""
        annual = []
        for day in range(days):
            day_of_week = (start_dow + day) % 7
            is_weekend = (day_of_week == 5) or (
                day_of_week == 6)  # Sat=5, Sun=6

            if is_weekend:
                daily = daily_profile * weekend_factor
            else:
                daily = daily_profile.copy()

            annual.extend(daily)

        return np.array(annual)

    def _extend_seasonal(self, daily_profile, weekend_factor, start_dow,
                         location, days=365):
        """Method 3: Seasonal + weekend"""
        # Seasonal multipliers
        seasonal_mults = {
            'southwest': {'winter': 0.95, 'spring': 1.00, 'summer': 1.05, 'fall': 1.00},
            'moderate': {'winter': 0.98, 'spring': 1.00, 'summer': 1.03, 'fall': 1.00}
        }
        mults = seasonal_mults.get(location, seasonal_mults['southwest'])

        annual = []
        for day in range(days):
            # Weekend
            day_of_week = (start_dow + day) % 7
            is_weekend = (day_of_week == 5) or (day_of_week == 6)

            # Season
            month = int((day % 365) / 30.4) + 1
            if month in [12, 1, 2]:
                season_mult = mults['winter']
            elif month in [3, 4, 5]:
                season_mult = mults['spring']
            elif month in [6, 7, 8]:
                season_mult = mults['summer']
            else:
                season_mult = mults['fall']

            # Combine
            if is_weekend:
                daily = daily_profile * weekend_factor * season_mult
            else:
                daily = daily_profile * season_mult

            annual.extend(daily)

        return np.array(annual)

    def _extend_stochastic(self, daily_profile, weekend_factor, start_dow,
                           location, noise_std, days=365):
        """Method 4: Seasonal + weekend + stochastic noise"""
        # Start with seasonal
        base = self._extend_seasonal(daily_profile, weekend_factor, start_dow,
                                     location, days)

        # Add day-to-day variation
        stochastic = []
        for day in range(days):
            daily_noise = np.random.normal(1.0, noise_std)
            daily_noise = np.clip(daily_noise, 0.90, 1.10)

            day_start = day * 24
            day_end = (day + 1) * 24
            day_profile = base[day_start:day_end] * daily_noise

            stochastic.extend(day_profile)

        return np.array(stochastic)

    def plot_annual_profile(self, df, title=None):
        """Plot annual load profile with statistics"""
        fig, axes = plt.subplots(3, 1, figsize=(14, 10))

        # Full year
        ax = axes[0]
        ax.plot(df['timestamp'], df['load_mw'], linewidth=0.5, alpha=0.7)
        ax.set_ylabel('Load (MW)', fontsize=11)
        ax.set_title(title or 'Annual Load Profile',
                     fontsize=13, fontweight='bold')
        ax.grid(True, alpha=0.3)

        # Add stats text
        stats_text = f"Annual avg: {df['load_mw'].mean():.1f} MW\n"
        stats_text += f"Peak: {df['load_mw'].max():.1f} MW\n"
        stats_text += f"Min: {df['load_mw'].min():.1f} MW\n"
        stats_text += f"Load factor: {df['load_mw'].mean()/df['load_mw'].max()*100:.1f}%\n"
        stats_text += f"Annual energy: {df['load_mw'].sum()/1000:.0f} GWh"
        ax.text(0.02, 0.98, stats_text, transform=ax.transAxes,
                fontsize=9, verticalalignment='top',
                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))

        # One week zoom
        ax = axes[1]
        week_data = df.iloc[:168]  # First week
        ax.plot(week_data['timestamp'],
                week_data['load_mw'], 'o-', linewidth=1.5)
        ax.set_ylabel('Load (MW)', fontsize=11)
        ax.set_title('First Week Detail', fontsize=12)
        ax.grid(True, alpha=0.3)

        # Monthly averages
        ax = axes[2]
        df['month'] = pd.to_datetime(df['timestamp']).dt.to_period('M')
        monthly_avg = df.groupby('month')['load_mw'].mean()
        ax.bar(range(len(monthly_avg)), monthly_avg.values,
               color='steelblue', alpha=0.7)
        ax.set_ylabel('Average Load (MW)', fontsize=11)
        ax.set_xlabel('Month', fontsize=11)
        ax.set_title('Monthly Average Load', fontsize=12)
        ax.set_xticks(range(12))
        ax.set_xticklabels(['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                           'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'])
        ax.grid(True, alpha=0.3, axis='y')

        plt.tight_layout()
        return fig


# Example usage
if __name__ == "__main__":
    # Initialize generator
    gen = SyntheticAILoadGenerator(nameplate_mw=100)

    # Generate all four scenarios using recommended method
    scenarios_to_generate = ['A', 'B', 'C', 'D']

    for scenario in scenarios_to_generate:
        print(f"\n=== Generating Scenario {scenario} ===")

        # Use seasonal method (good balance of realism and simplicity)
        df = gen.generate_annual_profile(
            scenario=scenario,
            method='seasonal',
            start_date='2026-01-01',
            location='southwest',
            random_seed=42
        )

        # Print summary
        print(f"Annual average: {df['load_mw'].mean():.1f} MW")
        print(f"Peak load: {df['load_mw'].max():.1f} MW")
        print(
            f"Load factor: {df['load_mw'].mean()/df['load_mw'].max()*100:.1f}%")
        print(f"Annual energy: {df['load_mw'].sum()/1000:.1f} GWh")

        # Save to CSV (compatible with off-grid AI calculator)
        filename = f"scenario_{scenario}_annual_load.csv"
        df.to_csv(filename, index=False)
        print(f"Saved to {filename}")

        # Plot (optional)
        # fig = gen.plot_annual_profile(df, title=f"Scenario {scenario}: {gen.scenarios[scenario]['name']}")
        # plt.savefig(f"scenario_{scenario}_plot.png", dpi=150)
        # plt.close()
