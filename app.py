import streamlit as st
import requests


# Page configuration
st.set_page_config(
    page_title='Universal Currency Converter',
    page_icon='💱',
    layout='centered'
)


# Application heading
st.title('🌍 Universal Currency Converter')

st.write('Convert currencies from around the world.')

st.divider()


# API endpoints
CURRENCIES_URL = 'https://api.frankfurter.dev/v2/currencies'
RATE_URL = 'https://api.frankfurter.dev/v2/rate'


# Fetch available currencies
@st.cache_data(ttl=86400)
def get_currencies():
    try:
        response = requests.get(CURRENCIES_URL, timeout=15)
        response.raise_for_status()

        data = response.json()

        if not isinstance(data, list):
            raise ValueError('Invalid currency data.')

        currencies = {
            item['iso_code']: item['name']
            for item in data
            if isinstance(item, dict)
            and isinstance(item.get('iso_code'), str)
            and isinstance(item.get('name'), str)
        }

        if not currencies:
            raise ValueError('No currencies available.')

        return dict(sorted(currencies.items()))

    except requests.exceptions.Timeout:
        raise RuntimeError(
            'The currency service timed out. Please try again.'
        ) from None

    except requests.exceptions.ConnectionError:
        raise RuntimeError(
            'Unable to connect. Check your internet connection.'
        ) from None

    except requests.exceptions.HTTPError as error:
        status = error.response.status_code

        raise RuntimeError(
            f'Currency service error: HTTP {status}.'
        ) from None

    except requests.exceptions.RequestException:
        raise RuntimeError(
            'A network error occurred while loading currencies.'
        ) from None

    except (ValueError, KeyError, TypeError):
        raise RuntimeError(
            'Unable to process the currency data.'
        ) from None


# Fetch exchange rates
@st.cache_data(ttl=3600)
def get_exchange_rate(from_currency, to_currency):
    try:
        url = f'{RATE_URL}/{from_currency}/{to_currency}'

        response = requests.get(url, timeout=15)
        response.raise_for_status()

        data = response.json()

        if not isinstance(data, dict):
            raise ValueError('Invalid exchange rate data.')

        rate = data.get('rate')
        rate_date = data.get('date')

        if (
            isinstance(rate, bool)
            or not isinstance(rate, (int, float))
            or rate <= 0
        ):
            raise ValueError('Invalid exchange rate.')

        if not isinstance(rate_date, str):
            raise ValueError('Missing exchange rate date.')

        return float(rate), rate_date

    except requests.exceptions.Timeout:
        raise RuntimeError(
            'The request timed out. Please try again.'
        ) from None

    except requests.exceptions.ConnectionError:
        raise RuntimeError(
            'Unable to connect to the exchange rate service.'
        ) from None

    except requests.exceptions.HTTPError as error:
        status = (
            error.response.status_code
            if error.response is not None
            else 'unknown'
        )

        if status == 404:
            raise RuntimeError(
                'No exchange rate was found for this currency pair.'
            ) from None

        raise RuntimeError(
            f'Exchange rate service error: HTTP {status}.'
        ) from None

    except requests.exceptions.RequestException:
        raise RuntimeError(
            'A network error occurred. Please try again.'
        ) from None

    except (ValueError, KeyError, TypeError):
        raise RuntimeError(
            'Unable to process the exchange rate data.'
        ) from None


# Load currencies
try:
    with st.spinner('Loading currencies...'):
        currencies = get_currencies()

except RuntimeError as error:
    st.error(str(error))

    if st.button('Retry'):
        get_currencies.clear()
        st.rerun()

    st.stop()


currency_codes = list(currencies.keys())


# Initialize session state
if 'amount' not in st.session_state:
    st.session_state.amount = 1000.0

if 'from_currency' not in st.session_state:
    st.session_state.from_currency = (
        'INR' if 'INR' in currency_codes else currency_codes[0]
    )

if 'to_currency' not in st.session_state:
    st.session_state.to_currency = (
        'USD' if 'USD' in currency_codes else currency_codes[-1]
    )

if 'conversion_result' not in st.session_state:
    st.session_state.conversion_result = None


# Validate saved currencies
if st.session_state.from_currency not in currency_codes:
    st.session_state.from_currency = currency_codes[0]

if st.session_state.to_currency not in currency_codes:
    st.session_state.to_currency = currency_codes[-1]


# Amount input
st.subheader('💰 Enter Amount')

amount = st.number_input(
    'Amount to convert',
    min_value=0.0,
    max_value=1_000_000_000_000.0,
    value=float(st.session_state.amount),
    step=100.0,
    format='%.2f',
    key='amount_input'
)

st.session_state.amount = amount


# Quick amount selection
st.write('**Quick Amount Selection**')

quick_columns = st.columns(5)

for column, quick_amount in zip(
    quick_columns,
    [100, 500, 1000, 5000, 10000]
):
    with column:
        if st.button(
            f'{quick_amount:,}',
            key=f'quick_{quick_amount}',
            use_container_width=True
        ):
            st.session_state.amount = float(quick_amount)
            st.rerun()


# Currency selection
st.subheader('🔄 Select Currencies')

col1, col2 = st.columns([5, 5])

with col1:
    from_currency = st.selectbox(
        'From',
        options=currency_codes,
        format_func=lambda code: (
            f'{code} - {currencies[code]}'
        ),
        index=currency_codes.index(
            st.session_state.from_currency
        ),
        key='from_selector'
    )

with col2:
    to_currency = st.selectbox(
        'To',
        options=currency_codes,
        format_func=lambda code: (
            f'{code} - {currencies[code]}'
        ),
        index=currency_codes.index(
            st.session_state.to_currency
        ),
        key='to_selector'
    )


# Update selected currencies
st.session_state.from_currency = from_currency
st.session_state.to_currency = to_currency


# Swap currencies
if st.button('🔁 Swap Currencies', use_container_width=True):
    st.session_state.from_currency, st.session_state.to_currency = (
        to_currency,
        from_currency
    )

    st.session_state.conversion_result = None
    st.rerun()


# Convert currency
if st.button(
    '💱 Convert Currency',
    type='primary',
    use_container_width=True
):
    st.session_state.conversion_result = None

    if amount <= 0:
        st.warning('Please enter an amount greater than zero.')

    elif from_currency == to_currency:
        st.session_state.conversion_result = {
            'amount': amount,
            'converted': amount,
            'from': from_currency,
            'to': to_currency,
            'rate': 1.0,
            'date': 'Same currency'
        }

    else:
        try:
            with st.spinner('Calculating conversion...'):
                rate, rate_date = get_exchange_rate(
                    from_currency,
                    to_currency
                )

                converted_amount = amount * rate

                st.session_state.conversion_result = {
                    'amount': amount,
                    'converted': converted_amount,
                    'from': from_currency,
                    'to': to_currency,
                    'rate': rate,
                    'date': rate_date
                }

        except RuntimeError as error:
            st.error(str(error))

        except (OverflowError, TypeError):
            st.error(
                'The conversion could not be completed. '
                'Please check the amount and try again.'
            )

        except Exception:
            st.error(
                'An unexpected error occurred. Please try again.'
            )


# Display conversion result
result = st.session_state.conversion_result

if result is not None:
    st.divider()
    st.subheader('📊 Conversion Result')

    col1, col2 = st.columns(2)

    with col1:
        st.metric(
            f'Amount ({result["from"]})',
            f'{result["amount"]:,.2f}'
        )

    with col2:
        st.metric(
            f'Converted ({result["to"]})',
            f'{result["converted"]:,.2f}'
        )

    st.success(
        f'1 {result["from"]} = '
        f'{result["rate"]:.6f} {result["to"]}'
    )

    st.caption(f'Exchange rate date: {result["date"]}')


# Application information
st.divider()

with st.expander('ℹ️ About the Converter'):
    st.write(
        'Convert between currencies supported by the '
        'Frankfurter exchange rate service.'
    )

    st.write(
        'Exchange rates are reference rates and may differ '
        'from rates offered by banks or money-transfer services.'
    )

    st.write(
        'Currency data is cached for 24 hours, while exchange '
        'rates are cached for one hour.'
    )


# Footer
st.caption(
    '🌍 Universal Currency Converter | '
    'Powered by the Frankfurter API'
)