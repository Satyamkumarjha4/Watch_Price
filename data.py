import re
import os
import pickle
import numpy as np
import pandas as pd
import config
from typing import List
from sklearn.preprocessing import MinMaxScaler, OneHotEncoder

class LoadData:
    def _load_data(self):
        if not os.path.exists(config.DATA_PATH):
            raise FileNotFoundError(f"File not found at {config.DATA_PATH}")
        
        self.df = pd.read_csv(config.DATA_PATH)

class PreprocessingData(LoadData):
    def _init_(self):
        super()._init_()
        self.on_encode = OneHotEncoder(sparse=False)
    
    def clean_df_predict(self, df=pd.DataFrame()):
        self.df = df
        self.df.drop_duplicates(inplace=True)
        self._remove_extra_col([config.EXTRA_COL])
        self._clean_display_col()
        self._clean_weight_col()
        self._create_discount_col()
        self._fill_na_num_col(False)
        self._scale_data()
        self._remove_na_cat_col()
        self.vectorise_cat_col(False)
        return self.df
    
    def clean_df(self):
        print("Cleaning data...")
        self._load_data()
        self.df.drop_duplicates(inplace=True)
        self._remove_extra_col([config.EXTRA_COL])
        self._clean_display_col()
        self._clean_weight_col()
        self._create_discount_col()
        self._remove_outliers_imp_col()
        self._fill_na_num_col()
        self._scale_data()
        self._remove_na_cat_col()
        self.vectorise_cat_col()
        self._save_clean_csv()
        print(f'Data cleaned and saved at {config.CLEAN_FILE_PATH}')
        return self.df
    
    def _remove_extra_col(self, col: List[str]):
        self.df.drop(col, axis=1, inplace=True)
        
    def _clean_display_col(self):
        self.df['Display Size'] = self.df['Display Size'].fillna('0.0 inches')
        self.df['Display Size'] = self.df['Display Size'].apply(lambda x: float(x.split()[0]))
        self.df['Display Size'] = self.df['Display Size'].replace(0.0, np.nan)
        
    def _clean_weight_col(self):
        def calculate_weight(val):
            numbers = re.findall(r'\d+', val)
            if numbers:
                return sum(int(x) for x in numbers) / len(numbers)
            return np.nan
        
        self.df['Weight'] = self.df['Weight'].apply(calculate_weight)
    
    def _create_discount_col(self):
        self.df['Discount'] = (self.df['Original Price']*(-self.df['Discount Percentage']))/100
        self.df.drop('Discount Percentage', axis=1, inplace=True)
        
    def _remove_outliers_IQR(self, data, col):
        Q1 = data[col].quantile(0.25)
        Q3 = data[col].quantile(0.75)
        IQR = Q3 - Q1
        lower_bound = Q1 - 1.5 * IQR
        upper_bound = Q3 + 1.5 * IQR
        return data[(data[col] > lower_bound) & (data[col] < upper_bound)]
    
    def _remove_outliers_from_imp_col(self):
        import_col = config.IMP_COL_NUMERICAL
        for col in import_col:
            self.df = self._remove_outliers_IQR(self.df, col)
    
    def _fill_na_num_col(self, save=True):
        if save:
            self.numerical_col = [
                feature for feature in self.df.columns if self.df[feature].dtype == 'float64']
            with open(os.path.join('dummys', 'numerical_col'), 'wb') as fp:
                pickle.dump(",".join(self.numerical_col), fp)
        else:
            with open(os.path.join('dummys', 'numerical_col'), 'rb') as fp:
                col = pickle.load(fp)
                self.numerical_col = col.split(',')
        for col in self.numerical_col:
            self.df[col].fillna(self.df[col].median(), inplace=True)

    def _scale_data(self):
        scaler = MinMaxScaler()
        data = scaler.fit_transform(self.df[self.numerical_col[:-1]])
        data = pd.DataFrame(data, columns=self.numerical_col[:-1])
        self.df.drop(self.numerical_col[:-1], axis=1, inplace=True)
        self.df = pd.concat([self.df.reset_index(), data], axis=1)
        
    def _remove_na_catogorical_col(self):
        self.imp_col = config.IMP_COL_CATOGORICAL
        for col in self.imp_col[1:]:
            self.df[col].fillna('other', inplace=True)

    def _vectorize_catogorical_col(self, save=True):
        brand_one_hot_df = self._one_hot_encode(
            self.df[['Brand']], 'Brand', save)
        model_name_one_hot_df = self._one_hot_encode(
            self.df[['Model Name']], 'Model Name', save)
        dial_shape_one_hot_df = self._one_hot_encode(
            self.df[['Dial Shape']], 'Dial Shape', save)
        strap_material_one_hot_df = self._one_hot_encode(
            self.df[['Strap Material']], 'Strap Material', save)

        self.df = pd.concat([self.df[self.numerical_col], brand_one_hot_df,
                            model_name_one_hot_df, dial_shape_one_hot_df, strap_material_one_hot_df], axis=1)

    def _one_hot_encode(self, series_data, name, save=True):
        if save:
            self.on_encode.fit(series_data)
            self._save_encoder(name, self.on_encode)
        else:
            self.on_encode = self._load_encoder(name)
        brand_onehot = self.on_encode.transform(series_data)
        categories = self.on_encode.categories_[0]
        onehot_columns = [f'{name}_{cat}' for cat in categories]
        return pd.DataFrame(brand_onehot, columns=onehot_columns)

    def _save_encoder(self, name, encoder):
        with open(os.path.join('dummys', name), 'wb') as fp:
            pickle.dump(encoder, fp)

    def _load_encoder(self, name):
        with open(os.path.join('dummys', name), 'rb') as fp:
            return pickle.load(fp)

    def _convert_list_to_dummy(self, series, li):
        temp_df = pd.DataFrame(columns=li)
        temp_df.loc[len(temp_df)] = [(lambda x: 1 if x == series.iloc[0] else 0)(x) for x in li]
        return temp_df

    def _save_to_csv(self):
        self.df.to_csv(config.CLEAN_FILE_PATH, index=False)