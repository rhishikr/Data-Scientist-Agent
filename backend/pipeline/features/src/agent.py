import pandas as pd
from .packs.time_series import add_time_features
from .packs.seasonality import add_seasonality
from .packs.price_promo import add_price_promo
from .packs.inventory import add_inventory_features

class FeatureEngineeringAgent:
    def __init__(self, date_col='date', key_cols=('store','sku'), target_col='qty', packs=None):
        self.date_col = date_col
        self.key_cols = list(key_cols)
        self.target_col = target_col
        self.packs = packs or {'time': True, 'seasonality': True, 'price_promo': True, 'inventory': True}

    def build(self, df: pd.DataFrame, horizon_days=1):
        df = df.sort_values([self.date_col] + self.key_cols).copy()
        # Add packs
        if self.packs.get('time', True):
            df = add_time_features(df, self.key_cols, self.target_col)
        if self.packs.get('seasonality', True):
            df = add_seasonality(df, self.date_col)
        if self.packs.get('price_promo', True):
            df = add_price_promo(df)
        if self.packs.get('inventory', True):
            df = add_inventory_features(df, self.key_cols)

        # Target (after features to avoid leakage): next-day qty by entity
        df['y'] = df.groupby(self.key_cols)[self.target_col].shift(-horizon_days)

        # Minimal feature set for demo
        feature_cols = [c for c in df.columns if c not in [self.target_col, 'y'] + [self.date_col] + self.key_cols]
        X = df.dropna(subset=['y'])[feature_cols].reset_index(drop=True)
        y = df.dropna(subset=['y'])['y'].reset_index(drop=True)
        return X, y, feature_cols
