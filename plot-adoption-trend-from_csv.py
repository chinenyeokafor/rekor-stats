import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
import matplotlib.ticker as mtick
import seaborn as sns
import matplotlib.ticker as mtick
import matplotlib.dates as mdates

# Set global font properties
plt.rcParams['font.size'] = 14  # Set default font size
plt.rcParams['axes.titlesize'] = 18  # Set title font size
plt.rcParams['axes.labelsize'] = 16  # Set axis label font size
plt.rcParams['xtick.labelsize'] = 14  # Set x-tick label font size
plt.rcParams['ytick.labelsize'] = 14  # Set y-tick label font size
plt.rcParams['legend.fontsize'] = 14  # Set legend font size

def format_yaxis(y, pos):
    if y >= 1e6:
        return f'{y / 1e6:.0f}M'
    elif y >= 1e3:
        return f'{y / 1e3:.0f}K'
    return int(y)

def plot_cummulative_plot(df):
    plt.figure(figsize=(10, 6))
    plt.plot(df['timestamp'], df['log_index'], label='Adoption Trend')
    plt.fill_between(df['timestamp'], df['log_index'],alpha=0.8)

    plt.xlabel('Timestamp', fontsize=16)
    plt.ylabel("# of entries", fontsize=16)
    plt.title('Adoption Trend Over Time', fontsize=18)
    plt.gca().yaxis.set_major_formatter(FuncFormatter(format_yaxis))
    plt.xticks(rotation=45)
    plt.tight_layout()
    # plt.legend()
    plt.savefig('results/adoption_trends/plot_cummulative_plot.png')

    # plt.show()


def plot_type_trend(df):

    all_types = df['type'].unique()
    plt.figure(figsize=(12, 6))

    colors = plt.cm.viridis(np.linspace(0, 1, len(all_types)))

    for i, entry_type in enumerate(all_types):
        type_data = df[df['type'] == entry_type]
        plt.plot(type_data['timestamp'], type_data['log_index'], label=entry_type, color=colors[i])

    plt.title('Adoption Trends by Type')
    plt.xlabel('Timestamp')
    plt.ylabel('# of entries')
    
    plt.gca().yaxis.set_major_formatter(FuncFormatter(format_yaxis))
    
    plt.xticks(rotation=45)
    plt.legend(loc='upper right', bbox_to_anchor=(1, 1), ncol=1)  
    plt.grid(True)

    plt.tight_layout()
    plt.savefig('results/adoption_trends/plot_type_trend.png')
    # plt.show()

def plot_types_as_lines(df):

    plt.figure(figsize=(12, 6))

    for entry_type, group in df.groupby('type'):
        plt.plot(group['timestamp'], group['log_index'], label=entry_type)


    plt.xlabel('Timestamp')
    plt.ylabel('# of entries')
    plt.title('Adoption Trend for Each Type')
    plt.gca().yaxis.set_major_formatter(FuncFormatter(format_yaxis))
    plt.xticks(rotation=45)
    plt.grid(True)
    plt.legend(title='Types')
    plt.tight_layout()
    plt.savefig('results/adoption_trends/plot_types_as_lines.png')
    # plt.show()

def daily_count_plot(df):
    df['date'] = df['timestamp'].dt.date

    daily_count = df.groupby('date').size().reset_index(name='count')
    daily_count['date'] = pd.to_datetime(daily_count['date'])

    plt.figure(figsize=(12, 6))
    plt.plot(daily_count['date'], daily_count['count'])
    plt.title('Daily Count of Rekor Entries')
    plt.xlabel('Date')
    plt.ylabel('Count of Entries')
    plt.xticks(rotation=45)
    plt.grid()
    plt.tight_layout()
    # plt.show()
    plt.savefig('results/adoption_trends/daily_count_plot.png')

def plot_daily_count_by_type(df):
    df['date'] = df['timestamp'].dt.date

    daily_type_count = df.groupby(['date', 'type']).size().reset_index(name='count')

    # print(daily_type_count)

    plt.figure(figsize=(12, 6))
    types = daily_type_count['type'].unique()

    palette = sns.color_palette("tab20", len(types))

    for i, entry_type in enumerate(types):
        type_data = daily_type_count[daily_type_count['type'] == entry_type]
        plt.plot(type_data['date'], type_data['count'],color=palette[i % len(palette)], alpha=1, label=entry_type)


    plt.title('Daily Count of Entries by Type')
    plt.xlabel('Timestamp')
    plt.ylabel('Count of Entries')
    plt.xticks(rotation=45)
    plt.grid()
    plt.legend(title='Entry Type', bbox_to_anchor=(1.05, 1), loc='upper right')  
    plt.tight_layout()
    
    plt.savefig('results/adoption_trends/daily_count_by_type.png')
    # plt.show()

def plot_monthly_count_by_type(df):

    df['year_month'] = df['timestamp'].dt.to_period('M').dt.to_timestamp()

    monthly_type_count = df.groupby(['year_month', 'type']).size().reset_index(name='count')

    # print(monthly_type_count)

    plt.figure(figsize=(12, 6))
    types = monthly_type_count['type'].unique()

    palette = sns.color_palette("tab20", len(types))

    for i, entry_type in enumerate(types):
        type_data = monthly_type_count[monthly_type_count['type'] == entry_type]
        plt.plot(type_data['year_month'], type_data['count'], 
                 color=palette[i % len(palette)], alpha=1, label=entry_type)

    plt.title('Monthly Count of Entries by Type')
    plt.xlabel('Year-Month')
    plt.ylabel('Count of Entries')

    plt.gca().yaxis.set_major_formatter(mtick.FuncFormatter(lambda x, _: f'{int(x):,}'))
    plt.gca().yaxis.set_major_formatter(FuncFormatter(format_yaxis))

    plt.gca().xaxis.set_major_locator(mdates.MonthLocator(interval=3))

    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))

    plt.xticks(rotation=45)
    plt.grid()
    plt.legend(title='Entry Type', bbox_to_anchor=(1.05, 1), loc='upper right')
    plt.tight_layout()
    
    plt.savefig('results/adoption_trends/monthly_count_by_type.png')
    # plt.show()


def init():
    df = pd.read_csv('results/all_rekor_dataset.csv')
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
    df = df.sort_values('timestamp')
    return df


if __name__ == "__main__":
    df = init()

    plot_cummulative_plot(df)
    plot_type_trend(df)
    plot_types_as_lines(df)
    daily_count_plot(df)
    plot_daily_count_by_type(df)
    plot_monthly_count_by_type(df)
    plot_type_trend(df)
    plot_types_as_lines(df)
    daily_count_plot(df)
    plot_daily_count_by_type(df)
    plot_monthly_count_by_type(df)