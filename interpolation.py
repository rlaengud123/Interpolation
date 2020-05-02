import numpy as np
import pandas as pd
import os
import datetime as dt
from math import cos
from scipy.interpolate import interp1d
from pysolar.solar import *
import argparse
from tqdm import trange, tqdm


parser = argparse.ArgumentParser(description='Interpolation')


parser.add_argument('--all_of_file', type=bool, default=False, help='If you want to convert many files, True (default : False)')
parser.add_argument('--file_name', type=str, help='File Name ex)2018010112_fcst.csv')
parser.add_argument('--time_type', type=str, help='12Z or 18Z')
parser.add_argument('--data_type', type=str, help='cumulative or mean or csi')
parser.add_argument('--method', type=str, help='linear or cubic')
parser.add_argument('--load_path', type=str, help='data load path')
parser.add_argument('--save_path', type=str, help='data save path')

args = parser.parse_args()

if args.all_of_file == False:
    save_file = os.path.join(args.save_path, args.file_name)


def preprocessing_mean(df, file_name, data_type):
    temp = df.iloc[:,2:]
    lat_lon = df.iloc[:, :2]
    sub_df = pd.DataFrame()
    for i in range(temp.shape[1]-1):
        sub_df = pd.concat([sub_df,pd.DataFrame( (temp.iloc[:,i+1] - temp.iloc[:,i]) / 3, columns=['{}'.format( (int(temp.columns[i+1])+int(temp.columns[i]))/2.0)])],axis=1)

    sub_df = np.maximum(0, sub_df)

    df = pd.concat([lat_lon, sub_df], axis=1)

    if data_type == 'csi':
        return df
        
    # 천정각 조건
    else:
        col_list = list(df.columns)
        time = file_name[0:8]
        KST = dt.timezone(dt.timedelta(hours=9))
        for i in trange(len(df)):
            for j in range(2, len(col_list)):
                datehour = dt.timedelta(hours=int(col_list[j][:len(col_list[j])-2]))
                date_time = dt.datetime.strptime(time, '%Y%m%d')
                date = date_time + datehour
                year = date.year
                month = date.month
                day = date.day
                hour = date.hour
                minute = 30

                date = dt.datetime(year, month, day, hour, minute, 0, tzinfo=KST)
                solar_angle = get_altitude(df['lat'][i],df['lon'][i],date)   # 태양천정각

                if solar_angle < 15:
                    df.iloc[i, j] = 0

        return df

def preprocessing_csi(df, file_name, data_type):
    df = preprocessing_mean(df, file_name, data_type)
    col_list = list(df.columns)
    time = file_name[0:8]

    KST = dt.timezone(dt.timedelta(hours=9))
    for i in trange(len(df)):
        for j in range(2, len(col_list)):
            datehour = dt.timedelta(hours=int(col_list[j][:len(col_list[j])-2]))
            date_time = dt.datetime.strptime(time, '%Y%m%d')
            date = date_time + datehour
            year = date.year
            month = date.month
            day = date.day
            hour = date.hour
            minute = 30

            date = dt.datetime(year, month, day, hour, minute, 0, tzinfo=KST)
            solar_angle = get_altitude(df['lat'][i],df['lon'][i],date)   # 태양천정각
            sza = float(90) - solar_angle

            new_value= sza*(math.pi/180)

            if solar_angle < 15:
                cosz = 0
                df.iloc[i, j] = 0
            else:
                cosz= math.cos(new_value)
                df.iloc[i, j] = df.iloc[i, j] / (1370 * cosz)
    
    return df



def interpolation(df, method, data_type):
    values = df.iloc[:, 2:]
    lat_lon = df.iloc[:, :2]
    
    x = list(map(float, values.columns))
    y = values
    f = interp1d(x, y, kind=method)
    columns = np.arange(x[0], x[-1]+0.1, 1)
    interp_x =columns.reshape(1, -1)
    interp_y = pd.DataFrame(f(interp_x).squeeze(), columns=columns)
    
    if data_type == 'mean' or 'csi':
        if method == 'cubic':   
            interp_y.iloc[:, 0:3] = 0
            interp_y = np.maximum(0, interp_y)


    if method == 'cubic':   
        if type == '12Z':
            interp_y.iloc[:, 0:9] = 0
        else:   # 18Z
            interp_y.iloc[:, 0:3] = 0
        
        interp_y = np.maximum(0, interp_y)

    return pd.concat([lat_lon, interp_y], axis=1)

     
def main():    
    if args.all_of_file == True:
        file_list = os.listdir(args.load_path)
        for file_name in tqdm(file_list):
            df = pd.read_csv(os.path.join(args.load_path, file_name))
            if args.data_type == 'mean':
                df = preprocessing_mean(df, file_name, args.data_type)

            if args.data_type == 'csi':
                df = preprocessing_csi(df, file_name, args.data_type)
            interpolation(df, args.method, args.data_type).to_csv(f'./{args.save_path}/{file_name}', index=False)
    
    else:
        df = pd.read_csv(os.path.join(args.load_path, args.file_name))
        if args.data_type == 'mean':
            df = preprocessing_mean(df, args.file_name, args.data_type)

        if args.data_type == 'csi':
            df = preprocessing_csi(df, args.file_name, args.data_type)
        interpolation(df, args.method, args.data_type).to_csv(f'./{args.save_path}/{args.file_name}', index=False)

if __name__=='__main__':
    main()