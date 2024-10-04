import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


# JavaScript function - wait for user interaction (click)
def wait_for_click(driver):
    driver.execute_script("""
        window.userClicked = false;
        document.addEventListener('click', function() {
            window.userClicked = true;
        });
    """)
    while True:
        user_clicked = driver.execute_script("return window.userClicked;")
        if user_clicked:
            spam_checkbox = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, '/html/body/table/tbody/tr[3]/td/form/table/tbody/tr[3]/td[3]/input')))
            learn = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, "/html/body/table/tbody/tr[3]/td/form/table/tbody/tr[3]/td[3]/select")))
            spam_report = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, '/html/body/table/tbody/tr[3]/td/form/table/tbody/tr[3]/td[3]/select/option[4]')))

            learn.click()
            spam_checkbox.click()
            spam_report.click()
            break 
        time.sleep(1)

def wait_for_user_click(driver, xpath='/html/body/table/tbody/tr[3]/td/form/table/tbody/tr[3]/td[3]/input'):
    # Wait for a change that occurs when the user clicks, such as a new element appearing
    WebDriverWait(driver, timeout=300).until(
        EC.presence_of_element_located((By.XPATH, xpath))
    )

    spam_checkbox = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, '/html/body/table/tbody/tr[3]/td/form/table/tbody/tr[3]/td[3]/input')))
    learn = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, "/html/body/table/tbody/tr[3]/td/form/table/tbody/tr[3]/td[3]/select")))
    spam_report = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, '/html/body/table/tbody/tr[3]/td/form/table/tbody/tr[3]/td[3]/select/option[4]')))
    submit_button = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, '/html/body/table/tbody/tr[3]/td/form/table/tbody/tr[4]/td[2]/button')))

    learn.click()
    spam_checkbox.click()
    spam_report.click()

    # Submit
    submit_button.click()

    # Go back 2x
    for x in range(0,2):
        driver.back()



url = "https://10.1.18.11"

#Create an instance of ChromeOptions - to customize behavior of the browser
chrome_options = webdriver.ChromeOptions()

# Keep browser open after code is executed
chrome_options.add_experimental_option("detach", True)

# This means the browser will remain open even after the script is done running.
driver = webdriver.Chrome(options=chrome_options)
driver.get(url)

# Maximize the browser window to take up the full screen.
driver.maximize_window()

# Accept it is not with security certificates
advanced = driver.find_element(By.XPATH, value='//*[@id="details-button"]')
advanced.click()
time.sleep(0.5) # Wait for loading webpage
proceed = driver.find_element(By.XPATH, value='//*[@id="proceed-link"]')
proceed.click()
time.sleep(1.5) # Wait for loading

# Find insert username and password
username = driver.find_element(By.XPATH, value='//*[@id="myusername"]')
username.send_keys("synergon")

password = driver.find_element(By.XPATH, value='//*[@id="mypassword"]')
password.send_keys("Synergon2017")

# Click login button
login_button = driver.find_element(By.XPATH, value='/html/body/div/div[2]/form/fieldset/p[5]/button')
login_button.click()

# Navigate to email box
search_and_reports = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, '//*[@id="menu"]/li[4]/a')))
search_and_reports.click()

message_listing = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, '/html/body/table/tbody/tr[3]/td/table/tbody/tr[10]/td/ul/li[1]/a')))
message_listing.click()

# Create loop - when user hit enter program will navigate to spam bar and hits "Spam + Report"

for click in range(0,100):
    wait_for_user_click(driver)


