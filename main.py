import os.path
import time

import pandas as pd
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC

import credentials
from selenium.webdriver.common.by import By
from seleniumbase import SB


VELES_URL = 'https://veles.finance/share/hfJwh'


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
                df.at[i, 'RR_Ratio'] = str(-1 * round(gross / mpu, 2))

            driver.find_element(By.XPATH, '//*[@id="app"]/main/section[4]/div[2]/ul/li[3]').click()
            time.sleep(2)
            max_orders = driver.find_element(By.XPATH, '//*[@id="app"]/main/section[4]/div[2]/div/div/div[2]/div/div[2]/div[1]/div/div[18]/div/p').text
            df.at[i, 'Max_Orders'] = max_orders.split('/')[0].strip()
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
        if credentials.AUTH_BY_GOOGLE:
            # часть со входом через гугл auth
            driver.find_element(By.ID, 'googleAuth').click()
            driver.type("#identifierId", credentials.GOOGLE_ACC)
            driver.click("#identifierNext > div > button")
            driver.type("#password > div.aCsJod.oJeWuf > div > div.Xb9hP > input", credentials.GOOGLE_PASS)
            driver.click("#passwordNext > div > button")
            time.sleep(5)
            print('We are ready to start!')
        else:
            # часть со входом обычным
            email_input = driver.find_element(By.NAME, 'username')
            email_input.send_keys(credentials.VELES_LOGIN)
            pass_input = driver.find_element(By.NAME, 'password')
            pass_input.send_keys(credentials.VELES_PASSWORD)
            enter_btn = driver.find_element(By.ID, 'submitButton')
            enter_btn.click()
            time.sleep(5)
            wait.until(EC.presence_of_element_located((By.CLASS_NAME, 'logout')))

        # включаем сортировку по кол-ву ордеров
        driver.find_element(By.XPATH, '//*[@id="app"]/main/section[4]/div[2]/ul/li[3]').click()
        time.sleep(2)
        driver.find_element(By.CSS_SELECTOR, '#app > main > section.backtest-tabs > div.backtest-tabs-deals.backtest-tabs > div > div > div.table-wrapper > div > div.head > div:nth-child(18)').click()

        return True

    except Exception as e:
        print(f"The Shit happens: {e}")
        return False


def find_element(driver, by: str, value: str) -> WebElement:
    element: WebElement = None
    while not element:
        element= driver.find_element(by, value)
    return element


def find_elements(driver, by: str, value: str) -> WebElement:
    elements: WebElement = None
    while not elements:
        elements= driver.find_elements(by, value)
    return elements


def proceed_next_coin(coin, driver, strategy_url, strategy_name):
    # загружаем образец бота
    driver.get(strategy_url)
    WebDriverWait(driver, 20).until(
        lambda d: d.execute_script("return document.readyState") == "complete"
    )
    time.sleep(2)  # 2 sec
    try:
        (find_element(driver, By.CSS_SELECTOR, '#app > main > section.backtest-header > div.backtest-header-middle.items-center > div.backtest-header-middle-buttons > button.backtest__run-bot.cursor-pointer.orange.button')
                    .click())
        time.sleep(3)  # 5 sec

        # меняем название теста добавляя монету и стратегию +12 sec
        (find_element(driver, By.CSS_SELECTOR, '#app > div > div.bot-editor__body > div.bot-editor__form > div.bot-editor__form-body > div.bot-form-block.bot-form-basic > div.bot-form-block__body > div.bot-form-basic__section.bot-form-basic__col > label > input[type=text]')
                    .send_keys(' # ' + coin + ' (' + strategy_name + ')'))
        # driver.find_element(By.CSS_SELECTOR,
        #                     '#app > div > div.bot-editor__body > div.bot-editor__form > div.bot-editor__form-body > div.bot-form-block.bot-form-basic > div.bot-form-block__body > div.bot-form-basic__section.bot-form-basic__col > label > input[type=text]').send_keys(
        #                                         ' # ' + coin + ' (' + strategy_name + ')')
        time.sleep(3) # 8 sec

        # Открываем выпадающий список монет
        (find_element(driver, By.CSS_SELECTOR, 'div.wrapper.pair.bot-form-basic__section > div.pair__bottom-wrapper > div > div:nth-child(1) > label > i')
                    .click())
        # driver.find_element(By.CSS_SELECTOR,
        #                     'div.wrapper.pair.bot-form-basic__section > div.pair__bottom-wrapper > div > div:nth-child(1) > label > i').click()
        time.sleep(3) #11

        # Находим нужную монету в списке и кликаем
        xpath = "//div[@class='select-item'][.//span[text()='" + coin + "']]"
        find_element(driver, By.XPATH, xpath).click()
        # driver.find_element(By.XPATH, xpath).click()
        time.sleep(3) #14

        # Жмём запустить бэктест
        find_element(driver, By.CLASS_NAME, 'bot-form-footer__backtests-button-name').click()
        # driver.find_element(By.CLASS_NAME, 'bot-form-footer__backtests-button-name').click()
        time.sleep(3) #17

        # Убираем галочку "Публичный тест"
        (find_element(driver, By.XPATH, "//div[@class='selects-wrapper']/label[contains(., 'Публичный тест')]/div[@class='checkbox']")
                    .click() )
        time.sleep(2) #19

        # Запускаем тест нажав на "Подтвердить" +22 sec
        (find_element(driver, By.XPATH, "//div[@class='popup-footer']//button")
                .click())
        # driver.find_element(By.XPATH, "//div[@class='popup-footer']//button").click()
        time.sleep(5) #24

        # Жмём кнопку "Поделиться" 27 sec
        (find_element(driver, By.CLASS_NAME, 'backtest-share')
                .click())
        # driver.find_element(By.CLASS_NAME, 'backtest-share').click()
        time.sleep(3) #27

        # Выделяем URL теста и сохраняем его +29 sec
        (find_element(driver, By.CSS_SELECTOR, '#app > div.popup-wrapper.add-telegram-popup.active > div.popup > div.popup-body > label > div')
                .click())
        time.sleep(2) #29
        link = driver.execute_script("return window.getSelection().toString();")
        print(link)
        time.sleep(2) #31

        return link

    except Exception as e:
        print(f"Error happened: {e}")
        return 'Error'


def run_the_test():
    with open('coins_list.txt', 'r') as file:
        coins_list = [line.strip() for line in file]
    print(f'Total Coins to test: {len(coins_list)}')

    if len(coins_list) > 0:

        tests_list = pd.read_csv('to_test.csv')

        chrome_args = [
            "--disable-sync",
            "--disable-notifications",
            "--no-default-browser-check",
            "--no-first-run",
            "--disable-infobars",
            "--start-maximized",
            "--disable-blink-features=AutomationControlled"
        ]
        with SB(uc=True, browser="chrome", enable_sync=False, chromium_arg=chrome_args) as opera_driver:
            if open_veles_page(opera_driver):
                tests_dirs = []
                # we are logged and ready
                for (i, test) in tests_list.iterrows():
                    tested_coins = []
                    test_links = []

                    test_url = test['url']
                    strategy_name = test['strategy']
                    for coin_name in coins_list:
                        # тест для монеты по стратегии
                        tested_coins.append(coin_name)
                        try:
                            backtest_link = proceed_next_coin(coin_name, opera_driver, test_url, strategy_name)
                        except Exception as e:
                            backtest_link = 'Error'
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
                    tests_dirs.append(test_dir)
                    print('Links are saved...')
                    time.sleep(1)

                for test_dir in tests_dirs:
                    results_file = test_dir + '/tests.csv'
                    df = pd.read_csv(results_file)
                    backtests_parsed_file_name = test_dir + '/results (parsed).csv'
                    parse_results(opera_driver, df, backtests_parsed_file_name)
            print('Parsing is finished...')


if __name__ == '__main__':
    run_the_test()
