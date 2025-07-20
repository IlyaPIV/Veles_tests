import os.path
import time

import pandas as pd
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

import credentials
from selenium.webdriver.common.by import By
from seleniumbase import SB


VELES_URL = 'https://veles.finance/share/tRlrW'
TEST_VERSION = 'Python Test v.0.0.0'



def match_label_to_column(label_text):
    match label_text:
        case 'Gross (USDT)':
            column_name = 'Gross'
        case 'Net (USDT)':
            column_name = 'Netto'
        case 'МПП':
            column_name = 'MPP'
        case 'МПУ':
            column_name = 'MPU'
        case 'Эффективность в день (USDT)':
            column_name = 'Effective'
        case 'Макс. сделка USDT':
            column_name = 'Deal_Gross_Max'
        case 'Средняя сделка USDT':
            column_name = 'Deal_Gross_Avg'
        case 'Всего':
            column_name = 'Total_Deals'
        case 'Среднее время в сделке':
            column_name = 'Deal_Time_Avg'
        case 'Макс. время в сделке':
            column_name = 'Deal_Time_Max'
        case _:
            column_name = 'skip'
    return column_name


def parse_results(driver, df, file_name_to_save):
    df['Gross'] = None
    df['Netto'] = None
    df['MPP'] = None
    df['MPU'] = None
    df['Effective'] = None
    df['Deal_Gross_Avg'] = None
    df['Deal_Gross_Max'] = None
    df['Total_Deals'] = None
    df['Deal_Time_Avg'] = None
    df['Deal_Time_Max'] = None
    df['Max_Orders'] = None
    df['RR_Ratio'] = None

    for i, row in df.iterrows():
        coin_name = row['Coin']
        print(f'Parsing {coin_name}: \n')
        url = row['Link']
        print(f' - URL -> {url}\n')
        if url == 'Error':
            continue
        try:
            driver.get(url)
            time.sleep(3)

            result_blocks = driver.find_elements(By.CLASS_NAME, 'backtest-result-card-wrapper-row')
            gross = 0
            mpu = 0
            for block in result_blocks:
                label = block.find_element(By.CLASS_NAME, 'backtest-result-card-wrapper-label').text
                value = block.find_element(By.CLASS_NAME, 'backtest-result-card-wrapper-value').text
                column_name = match_label_to_column(label)
                if column_name != 'skip':
                    if (column_name == 'MPU') or (column_name == 'MPP'):
                        value = value.split('USDT')[0].strip()
                    df.at[i, column_name] = value
                if column_name == 'MPU':
                    mpu = float(value)
                if column_name == 'Gross':
                    gross = float(value)

            if mpu != 0:
                df.at[i, 'RR_Ratio'] = str(-1 * round(gross / mpu, 2)) + ':1'

            driver.find_element(By.XPATH, '//*[@id="app"]/main/section[4]/div[2]/ul/li[3]').click()
            time.sleep(2)
            df.at[i, 'Max_Orders'] = driver.find_element(By.XPATH, '//*[@id="app"]/main/section[4]/div[2]/div/div/div[2]/div/div[2]/div[1]/div/div[18]/div/p').text
            time.sleep(2)

        except Exception as e:
            print(f'Error processing {url}: {e}')

    df.to_csv(file_name_to_save, index=False)


def open_veles_page(driver):
    # opening default test
    wait = WebDriverWait(driver, 10)
    driver.get(VELES_URL)
    wait.until(EC.presence_of_element_located((By.ID, 'googleAuth')))

    try:
        # часть со входом обычным
        # email_input = driver.find_element(By.NAME, 'username')
        # email_input.send_keys(VELES_LOGIN)
        # pass_input = driver.find_element(By.NAME, 'password')
        # pass_input.send_keys(VELES_PASSWORD)
        # enter_btn = driver.find_element(By.ID, 'submitButton')
        # enter_btn.click()

        # часть со входом через гугл auth
        driver.find_element(By.ID, 'googleAuth').click()
        driver.type("#identifierId", credentials.GOOGLE_ACC)
        driver.click("#identifierNext > div > button")
        driver.type("#password > div.aCsJod.oJeWuf > div > div.Xb9hP > input", credentials.GOOGLE_PASS)
        driver.click("#passwordNext > div > button")
        time.sleep(5)
        driver.find_element(By.XPATH, '//*[@id="app"]/main/section[4]/div[2]/ul/li[3]').click()
        time.sleep(2)
        driver.find_element(By.CSS_SELECTOR, '#app > main > section.backtest-tabs > div.backtest-tabs-deals.backtest-tabs > div > div > div.table-wrapper > div > div.head > div:nth-child(18)').click()
        print('We are ready to start!')
        return True
    except Exception as e:
        print(f"The Shit happens: {e}")
        return False


def proceed_next_coin(coin, driver, strategy_url, strategy_name):
    # загружаем образец стратегии и ждём 5 секунд
    driver.get(strategy_url)
    time.sleep(7)
    try:
        # кнопка "Запустить" +7 sec
        driver.find_element(By.CLASS_NAME, 'backtest__run-bot').click()
        time.sleep(5)
        # меняем название теста добавляя монету и стратегию +12 sec
        driver.find_element(By.XPATH,
                            '//*[@id="app"]/div/div[2]/div[2]/div[2]/div[1]/div[2]/div[1]/label/input').send_keys(
                                                ' # ' + coin + ' (' + strategy_name + ')')
        time.sleep(2)
        # Открываем выпадающий список монет +14 sec
        driver.find_element(By.XPATH,
                            '//*[@id="app"]/div/div[2]/div[2]/div[2]/div[1]/div[2]/div[2]/div[3]/div/div[1]/label/div').click()
        time.sleep(2)
        # Находим нужную монету в списке и кликаем +16 sec
        xpath = "//div[@class='select-item'][.//span[text()='" + coin + "']]"
        driver.find_element(By.XPATH, xpath).click()
        time.sleep(2)
        # Жмём запустить бэктест +18 sec
        driver.find_element(By.CLASS_NAME, 'bot-form-footer__backtests-button-name').click()
        time.sleep(2)
        # Убираем галочку "Публичный тест" +20 sec
        driver.find_element(By.XPATH,
                            '//*[@id="app"]/div/div[2]/div[2]/div[3]/div[1]/div[1]/div[2]/div[2]/div[1]/label[1]/div').click()
        time.sleep(2)
        # Запускаем тест нажав на "Подтвердить" +22 sec
        driver.find_element(By.XPATH, "//div[@class='popup-footer']//button").click()
        time.sleep(5)
        # Жмём кнопку "Поделиться" 27 sec
        driver.find_element(By.CLASS_NAME, 'backtest-share').click()
        time.sleep(2)
        # Выделяем URL теста и сохраняем его +29 sec
        driver.find_element(By.XPATH, '//*[@id="app"]/div[4]/div[2]/div[2]/label/div').click()
        link = driver.execute_script("return window.getSelection().toString();")
        time.sleep(1)
        # Просто ждём ещё 1 секунду +30 sec
        return link

    except Exception as e:
        print(f"Error happened: {e}")
        return 'Error'


def run_the_test():
    with open('coins_list.txt', 'r') as file:
        coins_list = [line.strip() for line in file]
    print(f'Total Coins to test: {len(coins_list)}')

    if len(coins_list) > 0:
        tested_coins = []
        test_links = []

        tests_list = pd.read_csv('to_test.csv')

        with SB(uc=True) as opera_driver:
            if open_veles_page(opera_driver):
                # we are logged and ready
                for (i, test) in tests_list.iterrows():
                    test_url = test['url']
                    strategy_name = test['strategy']
                    for coin_name in coins_list:
                        # тест для монеты по стратегии
                        tested_coins.append(coin_name)
                        backtest_link = proceed_next_coin(coin_name, opera_driver, test_url, strategy_name)
                        test_links.append(backtest_link)
        print('Test is finished. Saving results...')
        results = {
            "Coin": tested_coins,
            "Link": test_links
        }

        df = pd.DataFrame(results)

        test_dir = './'+strategy_name
        if not os.path.isdir(test_dir):
            os.makedirs(test_dir)
        backtests_result_file_name = './' + strategy_name + '/tests.csv'
        df.to_csv(backtests_result_file_name, index=False)
        print('Links are saved...')
        time.sleep(1)
        backtests_parsed_file_name = './' + strategy_name + '/results (parsed).csv'
        parse_results(opera_driver, df, backtests_parsed_file_name)
        print('Parsing is finished...')


def only_parsing():
    with SB(uc=True) as opera_driver:
        if open_veles_page(opera_driver):
            df = pd.read_csv('backtests.csv')
            backtests_parsed_file_name = TEST_VERSION + ' (parsed).csv'
            parse_results(opera_driver, df, backtests_parsed_file_name)
            print('Parsing is finished...')


if __name__ == '__main__':
    #run_the_test()
    only_parsing()
