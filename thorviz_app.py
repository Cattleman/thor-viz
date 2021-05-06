import json
from datetime import datetime, timedelta
from typing import Optional, List, Tuple

# Core
import pandas as pd
import plotly.express as px
import requests
import streamlit as st
import streamlit.components.v1 as components
import numpy as np
import ftx

########################################################################################
# Config
########################################################################################

COINS = ["RUNE","BNB","BTC","ETH",]

########################################################################################
# Data
########################################################################################

def get_market_price() -> float:
    
    ftx_client = ftx.FtxClient()
    
    result = ftx_client.get_market('RUNE/USD')
    
    market_price = result['price']
    
    return market_price

@st.cache(suppress_st_warning=True, allow_output_mutation=True)
def get_rune_stats() -> Dict[str, float]:
    
    '''
    Slaw's method.
    '''
    
    market_price = get_market_price()
    
    # MCCN
    mccn = requests.get('https://midgard.thorchain.info/v2/network')
    mccn_dict = mccn.json()
    
    mccn_total_pooled_rune = float(mccn_dict['totalPooledRune']) / 1e7
    mccn_total_active_bond = float(mccn_dict['bondMetrics']['totalActiveBond']) / 1e7 
    
    # ---
    
    # SCCN
    sccn = requests.get('http://thorb.sccn.nexain.com:8080/v1/network')
    sccn_dict = sccn.json()
    
    sccn_total_staked_rune = float(sccn_dict['totalStaked']) / 1e7
    sccn_total_active_bond = float(sccn_dict['bondMetrics']['totalActiveBond']) / 1e7 
    
    # calculations
    
    rune_in_lp_count = mccn_total_pooled_rune + sccn_total_staked_rune
    rune_bonded_count = mccn_total_active_bond + sccn_total_active_bond
    
    total_in_network_count = rune_in_lp_count + rune_bonded_count
    
    deterministic_value = rune_in_lp_count * market_price * 3 # In USD
    
    determined_price = deterministic_value / total_in_network_count # In USD
    
    speculation = market_price - determined_price # USD
    
    speculation_pct = speculation / market_price
    
    # Collect Results
    result_dict = {
        'Rune_in_LP_count': rune_in_lp_count,
        'Rune_bonded_count': rune_bonded_count,
        'total_in_network_count': total_in_network_count,
        'deterministic_value_usd': deterministic_value,
        'determined_price': determined_price,
        'market_price_usd': market_price,
        'speculation_premium_usd': speculation,
        'speculation_pct_of_market': speculation_pct,
    }
    
    return result_dict 



@st.cache(suppress_st_warning=True, allow_output_mutation=True)
def fetch_network_rune_data() -> pd.DataFrame:

    '''
    Gathers network Rune values for calculating in-network rune.
    
    Documentation: https://testnet.midgard.thorchain.info/v2/doc#operation/GetNetworkData
    '''
    
    network_data_request = 'https://midgard.thorchain.info/v2/network'
    rn = requests.get(network_data_request)
    net_response_dict = rn.json()
    
    _df = pd.DataFrame([net_response_dict['bondMetrics']]).astype(float)
    
    _df['totalPooledRune'] = float(net_response_dict['totalPooledRune'])
    _df['totalReserve'] = float(net_response_dict['totalReserve'])
    
    return _df


@st.cache(suppress_st_warning=True, allow_output_mutation=True)
def get_rune_market_price_and_depth() -> Tuple[float, float]:
    
    '''
    Get the the price of Rune based on the deepest USD pool and the current total Rune in the pools.
    
    Documentation: https://testnet.midgard.thorchain.info/v2/doc#operation/GetStats
    
    '''
    
    my_request = 'https://midgard.thorchain.info/v2/stats'
    
    r = requests.get(my_request)
    response_dict = r.json()
    
    rune_price = np.round(float(response_dict['runePriceUSD']), 2)
    total_pooled_rune = float(response_dict['runeDepth']) / 1e7
    
    
    return  rune_price, total_pooled_rune 

@st.cache(suppress_st_warning=True, allow_output_mutation=True)
def get_multichain_pool_data() -> pd.DataFrame:
   
    # TODO - doc string

    my_request = 'https://midgard.thorchain.info/v2/pools'
    
    r = requests.get(my_request)
    response_dict = r.json()
    
    
    return pd.DataFrame(response_dict)
    

#@st.cache(suppress_st_warning=True, allow_output_mutation=True)
def calculate_non_rune_TVL(df) -> float:
    '''
    Calulates total non Rune value locked in the Network by summing
    all Pool USD value.
    '''
    df = df.copy()
    
    df['total_value_USD'] = df['assetPriceUSD'].astype(float) * (df['assetDepth'].astype(float) / 1e7 )
    
    # Divide by 2 here b/c half the value is in Rune, half in the asset.
    total_non_rune_tvl = df['total_value_USD'].sum() / 2
    
    return total_non_rune_tvl


########################################################################################
# Helpers
########################################################################################



########################################################################################
# App
########################################################################################


# ------------------------------ Config ------------------------------

st.set_page_config(
    page_title="ThorViz", page_icon="⚡", layout="wide",
    #initial_sidebar_state="expanded"
)


# ------------------------------ Sidebar ------------------------------

st.sidebar.title("Config")

#days = st.sidebar.slider("Days:", value=60, min_value=0, max_value=60)
primary = st.sidebar.selectbox("Primary:", COINS)
#compare = st.sidebar.multiselect("Compare: ", COINS)


# ------------------------------ Trading View Ticker ------------------------------

# format ticker coins for javascript input
tv_ticker_coins = list(
    map(lambda c: {"proName": f"BINANCE:{c}USDT", "title": f"{c}/USD"}, COINS)
)
components.html(
    f"""
<div class="tradingview-widget-container">
  <div class="tradingview-widget-container__widget"></div>
  <div class="tradingview-widget-copyright">
    <a href="https://www.tradingview.com" rel="noopener" target="_blank">
    <script
        type="text/javascript"
        src="https://s3.tradingview.com/external-embedding/embed-widget-ticker-tape.js"
        async
    >
      {{
        "symbols": {json.dumps(tv_ticker_coins)},
        "isTransparent": false,
        "locale": "en"
      }}
    </script>
  </div>
</div>
""",
    height=80,
)

# ------------------------------ Header  ------------------------------

# This is a hack to align center :-(

col1, col2, col3 = st.beta_columns([1,6,1])


with col1:
    st.write("")

with col2:
    st.title("ThorViz - Thorchain Tokenomics Dashboard")
    st.title('⚡⚡⚡ #RAISETHECAPS ⚡⚡⚡')

with col3:
    st.write("")
# ------------------------------ Trading View Chart ------------------------------

with st.beta_expander("Market (Binance)"):

    components.html(
        f"""
    <div class="tradingview-widget-container">
      <div id="tradingview_49e5b"></div>
      <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
      <script type="text/javascript">
      new TradingView.widget(
      {{
      "symbol": "BINANCE:{primary}USDT",
      "interval": "4H",
      "timezone": "Etc/UTC",
      "style": "1",
      "locale": "en",
      "toolbar_bg": "#f1f3f6",
      "enable_publishing": false,
      "allow_symbol_change": true,
      "container_id": "tradingview_49e5b"
      }}
      );
      </script>
    </div>
    """,
        height=550,
        width=900,
    )


# ------------------------------ Sections ------------------------------

st.error("This dashboard is in beta, there may be bugs.")
if st.button("I understand there could be bugs, let me in!"):


    with st.beta_expander("Rune Baseline Price"):
    
        st.write('RUNE TO MOON!')
        st.write(f'Data Source for MCCN: {"https://midgard.thorchain.info/v2/network"}')
        network_df = fetch_network_rune_data()

        # This method of calculating total_pooled_rune is simplified below
        #total_pooled_rune = network_df['totalPooledRune'][0].astype(float) / 1e7
        
        #total_reserve = network_df['totalReserve'][0].astype(float) / 1e7

        total_active_bond = network_df['totalActiveBond'][0].astype(float) / 1e7
        total_standby_bond = network_df['totalStandbyBond'][0].astype(float) / 1e7
        

        # Market Price, total pooled_rune
        rune_market_price, total_pooled_rune = get_rune_market_price_and_depth()
        
        #rune_list = [
         #       total_pooled_rune,
                #total_reserve, # EXCLUDE from in-network calculation!
          #      total_active_bond,
               # total_standby_bond # excluded per Slaw   
           # ]

        # TRYING to match Slaw by subtracting `total_standby_bond`
        total_rune_in_network = np.round(total_pooled_rune + total_active_bond , 2) - total_standby_bond
        
        # Get MCCN Pool data
        mccn_pool_df = get_multichain_pool_data()

        # Calculate non-Rune TVL
        nonrune_tvl = calculate_non_rune_TVL(df=mccn_pool_df)
        
        # Deterministic Value in USD
        deterministic_value = 3 * nonrune_tvl # 3:1

        
        baseline_price = deterministic_value / total_rune_in_network
        
        in_net_speculation_premium = rune_market_price - baseline_price
        
        # Spec in percentage terms
        speculation_pct = 100 * np.round(in_net_speculation_premium, 2)/ np.round(rune_market_price, 2)
        
        # `:,` formats values with comma for easier reading.

        st.write(f'total_pooled_rune: {np.round(total_pooled_rune, 2):,}')
        #st.write(f'total_reserve_rune: {np.round(total_reserve, 2):,}')
        st.write(f'total_active_bond_rune: {np.round(total_active_bond, 2):,}')
        st.write(f'total_standby_bond_rune: {np.round(total_standby_bond, 2):,}')
        st.write('-'* 30)
        
        # Calculate Baseline Price
        st.write(f"nonRUNE TVL: {np.round(nonrune_tvl, 2):,}")
        st.write(f"Deterministic Value: ${np.round(deterministic_value, 2):,}")
        st.write(f"in-network RUNE: {np.round(total_rune_in_network,2):,}")
        st.write(f"Market Price (USD): ${np.round(rune_market_price, 2):,}")
        st.write(f"Baseline Price (USD): ${np.round(baseline_price, 2):,}")
        st.write(f"Speculation Premium (USD): ${np.round(in_net_speculation_premium, 2) :,}")
        st.write(f'Speculation as a percentage of Market Price: {np.round(speculation_pct,2)}%')


    with st.beta_expander("new calculation method"):
        
        # Method directly from Slaw
        
        

        RUNE_in_LP_count = totalStaked_SCCN + totalPooleRune_MCCN
        RUNE_bonded_count = totalActiveBond_SCCN + totalActiveBond_MCCN

        total_in_network_count = RUNE_in_LP_count + RUNE_bonded_count

        deterministic_value = RUNE_in_LP_count * market_price * 3
        determined_price = deterministic_value / total_in_network_count
        speculation = market_price - determined_price


    # TODO add additional tools
    #with st.beta_expander("Pool Stats"):

     #   st.write('Pool STATS go here...')

    #with st.beta_expander("Social"):
    #    st.write('Social data coming soon...') 
