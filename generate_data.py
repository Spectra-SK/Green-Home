import os

import numpy as np
import pandas as pd


def generate_synthetic_dataset(n_properties=5000, output_dir="data"):
    np.random.seed(42)
    os.makedirs(output_dir, exist_ok=True)

    # 1. Generate Customers (ensures ~15% multi-property ownership to test data leakage)
    n_customers = int(n_properties * 0.85)
    customer_ids_pool = [f"C{str(i).zfill(5)}" for i in range(1, n_customers + 1)]
    customer_ids = np.random.choice(customer_ids_pool, size=n_properties)
    property_ids = [f"P{str(i).zfill(6)}" for i in range(1, n_properties + 1)]

    # 2. Physical Characteristics
    regions = np.random.choice(
        ['London', 'South East', 'North West', 'Midlands', 'Scotland', 'Wales'],
        size=n_properties, p=[0.18, 0.22, 0.20, 0.18, 0.12, 0.10]
    )
    property_types = np.random.choice(
        ['Detached', 'Semi-Detached', 'Terraced', 'Flat'],
        size=n_properties, p=[0.25, 0.35, 0.25, 0.15]
    )
    property_ages = np.random.choice(
        ['Pre-1930', '1930-1982', '1983-2012', 'Post-2012'],
        size=n_properties, p=[0.20, 0.40, 0.25, 0.15]
    )
    floor_area = np.random.gamma(shape=5.0, scale=19.0, size=n_properties).clip(45, 300).round(1)
    bedrooms = np.clip(np.floor(floor_area / 42) + np.random.choice([0, 1], size=n_properties, p=[0.75, 0.25]), 1, 5).astype(int)

    # Realistic EPC Ratings (UK benchmark distribution)
    epc_ratings = np.random.choice(['A', 'B', 'C', 'D', 'E', 'F', 'G'], size=n_properties, p=[0.03, 0.12, 0.34, 0.32, 0.12, 0.05, 0.02])

    # 3. Features correlated with EPC
    heating_types = []
    insulation_levels = []
    glazing_types = []
    solar_panels = []
    smart_controls = []

    for epc in epc_ratings:
        if epc in ['A', 'B']:
            heating_types.append(np.random.choice(['Heat Pump', 'Gas Boiler'], p=[0.70, 0.30]))
            insulation_levels.append(np.random.choice(['Good', 'Moderate'], p=[0.85, 0.15]))
            glazing_types.append(np.random.choice(['Triple', 'Double'], p=[0.40, 0.60]))
            solar_panels.append(np.random.choice([True, False], p=[0.65, 0.35]))
            smart_controls.append(np.random.choice([True, False], p=[0.80, 0.20]))
        elif epc in ['C', 'D']:
            heating_types.append(np.random.choice(['Gas Boiler', 'Heat Pump', 'Electric Storage'], p=[0.80, 0.10, 0.10]))
            insulation_levels.append(np.random.choice(['Good', 'Moderate', 'Poor'], p=[0.20, 0.65, 0.15]))
            glazing_types.append(np.random.choice(['Double', 'Single'], p=[0.85, 0.15]))
            solar_panels.append(np.random.choice([True, False], p=[0.15, 0.85]))
            smart_controls.append(np.random.choice([True, False], p=[0.40, 0.60]))
        else:  # E, F, G
            heating_types.append(np.random.choice(['Gas Boiler', 'Oil Boiler', 'Electric Storage'], p=[0.60, 0.25, 0.15]))
            insulation_levels.append(np.random.choice(['Moderate', 'Poor'], p=[0.20, 0.80]))
            glazing_types.append(np.random.choice(['Double', 'Single'], p=[0.30, 0.70]))
            solar_panels.append(False)
            smart_controls.append(False)

    heating_types = np.array(heating_types)
    insulation_levels = np.array(insulation_levels)
    glazing_types = np.array(glazing_types)
    solar_panels = np.array(solar_panels)
    smart_controls = np.array(smart_controls)

    # 4. Energy Consumption (Metered Physics)
    base_heat_intensity = np.random.uniform(110, 160, size=n_properties)
    insul_mult = np.select([insulation_levels == 'Poor', insulation_levels == 'Moderate', insulation_levels == 'Good'], [1.35, 1.0, 0.70])
    glaze_mult = np.select([glazing_types == 'Single', glazing_types == 'Double', glazing_types == 'Triple'], [1.15, 1.0, 0.90])

    raw_heating_demand = floor_area * base_heat_intensity * insul_mult * glaze_mult

    # Gas & Electricity baseline consumption
    gas_kwh = np.where(heating_types == 'Heat Pump', 0.0, raw_heating_demand * 1.15).round(1)

    base_elec = floor_area * np.random.uniform(25, 40, size=n_properties)
    heat_pump_elec = np.where(heating_types == 'Heat Pump', raw_heating_demand / 3.2, 0.0)
    solar_offset = np.where(solar_panels, np.minimum(2500, (base_elec + heat_pump_elec) * 0.35), 0.0)
    elec_kwh = np.maximum(800.0, base_elec + heat_pump_elec - solar_offset).round(1)

    # 5. Baseline Property Value (with regional variance)
    region_multiplier = np.select(
        [regions == 'London', regions == 'South East', regions == 'North West', regions == 'Midlands', regions == 'Scotland', regions == 'Wales'],
        [1.85, 1.40, 0.95, 0.90, 0.85, 0.80]
    )
    base_sqm_price = 3200 * region_multiplier
    current_value = (floor_area * base_sqm_price + bedrooms * 20000 + np.random.normal(30000, 10000, size=n_properties)).round(-2)

    # 6. Reference Targets for ML Training (Sections 3, 7, 9)
    # Improvement potential: % reduction in purchased energy achievable via full retrofit package
    theoretical_post_gas = np.zeros(n_properties)  # Heat pump transition
    theoretical_post_elec = np.maximum(800.0, (base_elec + (floor_area * 80.0 / 3.2)) - 2500.0)  # Insulated + HP + Solar

    baseline_purchased = elec_kwh + gas_kwh
    post_purchased = theoretical_post_elec + theoretical_post_gas
    improvement_potential_pct = np.clip(100.0 * (baseline_purchased - post_purchased) / baseline_purchased, 0.0, 75.0).round(2)

    # Indicative property value uplift target percentage (UK market EPC uplift: 2% to 8%)
    epc_uplift_pct = np.select(
        [epc_ratings == 'A', epc_ratings == 'B', epc_ratings == 'C', epc_ratings == 'D', epc_ratings == 'E', epc_ratings == 'F', epc_ratings == 'G'],
        [0.01, 0.02, 0.035, 0.05, 0.065, 0.08, 0.095]
    )
    target_value_uplift_pct = (epc_uplift_pct + np.random.normal(0.0, 0.008, size=n_properties)).clip(0.01, 0.12).round(4)

    df = pd.DataFrame({
        'property_id': property_ids,
        'customer_id': customer_ids,
        'region': regions,
        'property_type': property_types,
        'property_age': property_ages,
        'floor_area': floor_area,
        'bedrooms': bedrooms,
        'epc_rating': epc_ratings,
        'heating_type': heating_types,
        'insulation': insulation_levels,
        'glazing': glazing_types,
        'solar': solar_panels,
        'smart_controls': smart_controls,
        'baseline_gas_kwh': gas_kwh,
        'baseline_elec_kwh': elec_kwh,
        'current_value': current_value,
        'target_improvement_potential_pct': improvement_potential_pct,
        'target_value_uplift_pct': target_value_uplift_pct
    })

    # 7. Customer-Level Train/Val/Test Split (Section 9 Requirement: NO DATA LEAKAGE)
    unique_customers = np.array(df['customer_id'].unique(), dtype=object)
    np.random.shuffle(unique_customers)
    n_cust = len(unique_customers)

    train_cust = unique_customers[:int(n_cust * 0.80)]
    val_cust = unique_customers[int(n_cust * 0.80):int(n_cust * 0.90)]
    test_cust = unique_customers[int(n_cust * 0.90):]

    train_df = df[df['customer_id'].isin(train_cust)]
    val_df = df[df['customer_id'].isin(val_cust)]
    test_df = df[df['customer_id'].isin(test_cust)]

    df.to_csv(os.path.join(output_dir, "synthetic_properties_full.csv"), index=False)
    train_df.to_csv(os.path.join(output_dir, "train.csv"), index=False)
    val_df.to_csv(os.path.join(output_dir, "val.csv"), index=False)
    test_df.to_csv(os.path.join(output_dir, "test.csv"), index=False)

    print(f"Generated {len(df)} properties across {n_cust} unique customers.")
    print(f"Train: {len(train_df)}, Val: {len(val_df)}, Test: {len(test_df)}")

if __name__ == "__main__":
    generate_synthetic_dataset()
