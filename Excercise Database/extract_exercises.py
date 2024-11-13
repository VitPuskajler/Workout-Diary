# I need to extract excecises from some relevant site
# https://www.jefit.com

import time
import requests
import selenium
from bs4 import BeautifulSoup

PATH_TO_CURRENT_FOLDER = r"C:\Users\vit.puskajler\Documents\Study materials\Python\Projekty\Workout Periodization\Excercise Database"

# My first decorator
def sleep_initiator(function):
    def wrapper_function():    
        time.sleep(3)
        return function()
    return wrapper_function

# Get hold of abs excercises
def abs_to_save():
    abs_page_c = 1
    while abs_page_c != 25:
        url_abs = f"https://www.jefit.com/exercises/bodypart.php?id=0&exercises=Abs&All=0&Bands=0&Bench=0&Dumbbell=0&EZBar=0&Kettlebell=0&MachineStrength=0&MachineCardio=0&Barbell=0&BodyOnly=0&ExerciseBall=0&FoamRoll=0&PullBar=0&WeightPlate=0&Other=0&Strength=0&Stretching=0&Powerlifting=0&OlympicWeightLifting=0&Beginner=0&Intermediate=0&Expert=0&page={abs_page_c}"
        r_abs = requests.get(url_abs)

        soup = BeautifulSoup(r_abs.content, "html.parser")

        excercises = soup.find_all(style='color:#0E709A;')

        for excercise in excercises:
            to_save = excercise.getText()
            with open(f"{PATH_TO_CURRENT_FOLDER}/abs_excerxises.txt", "a") as back_file:
                back_file.write(f"{to_save}\n")
                print(f"Excercise: {to_save} added to .txt file")
        abs_page_c += 1
        time.sleep(2)

def back_to_save():
    back_page_c = 1
    while back_page_c != 19 :
        url_back = f"https://www.jefit.com/exercises/bodypart.php?id=1&exercises=Back&All=0&Bands=0&Bench=0&Dumbbell=0&EZBar=0&Kettlebell=0&MachineStrength=0&MachineCardio=0&Barbell=0&BodyOnly=0&ExerciseBall=0&FoamRoll=0&PullBar=0&WeightPlate=0&Other=0&Strength=0&Stretching=0&Powerlifting=0&OlympicWeightLifting=0&Beginner=0&Intermediate=0&Expert=0&page={back_page_c}"
        r_back = requests.get(url_back)

        soup = BeautifulSoup(r_back.content, "html.parser")

        excercises = soup.find_all(style='color:#0E709A;')

        for excercise in excercises:
            to_save = excercise.getText()
            with open(f"{PATH_TO_CURRENT_FOLDER}/back_excerxises.txt", "a") as back_file:
                back_file.write(f"{to_save}\n")
                print(f"Saved:{to_save}")
        back_page_c += 1

def biceps_to_save():
    biceps_to_page_c = 1
    while biceps_to_page_c != 13 :
        url_back = f"https://www.jefit.com/exercises/bodypart.php?id=2&exercises=Biceps&All=0&Bands=0&Bench=0&Dumbbell=0&EZBar=0&Kettlebell=0&MachineStrength=0&MachineCardio=0&Barbell=0&BodyOnly=0&ExerciseBall=0&FoamRoll=0&PullBar=0&WeightPlate=0&Other=0&Strength=0&Stretching=0&Powerlifting=0&OlympicWeightLifting=0&Beginner=0&Intermediate=0&Expert=0&page={biceps_to_page_c}"
        r_bic = requests.get(url_back)

        soup = BeautifulSoup(r_bic.content, "html.parser")

        excercises = soup.find_all(style='color:#0E709A;')

        for excercise in excercises:
            to_save = excercise.getText()
            with open(f"{PATH_TO_CURRENT_FOLDER}/biceps_excerxises.txt", "a") as back_file:
                back_file.write(f"{to_save}\n")
                print(f"Saved: {to_save}")
        biceps_to_page_c += 1    

# I want to make it easier to manipulate with
# @sleep_initiator
def excercises_to_save(url, how_many_pages_url: int, bodypart:str):
    current_page = 1
    while current_page != how_many_pages_url + 1:
        url_back = f"{url}{current_page}"
        r_bic = requests.get(url_back)

        soup = BeautifulSoup(r_bic.content, "html.parser")

        excercises = soup.find_all(style='color:#0E709A;')

        for excercise in excercises:
            to_save = excercise.getText()
            with open(f"{PATH_TO_CURRENT_FOLDER}/{bodypart}.txt", "a") as file:
                file.write(f"{to_save}\n")
                print(f"Saved: {to_save}")
        current_page += 1    

chest_url = "https://www.jefit.com/exercises/bodypart.php?id=3&exercises=Chest&All=0&Bands=0&Bench=0&Dumbbell=0&EZBar=0&Kettlebell=0&MachineStrength=0&MachineCardio=0&Barbell=0&BodyOnly=0&ExerciseBall=0&FoamRoll=0&PullBar=0&WeightPlate=0&Other=0&Strength=0&Stretching=0&Powerlifting=0&OlympicWeightLifting=0&Beginner=0&Intermediate=0&Expert=0&page="
excercises_to_save(chest_url, 14, "chest_excercises")

forearm_url = "https://www.jefit.com/exercises/bodypart.php?id=4&exercises=Forearm&All=0&Bands=0&Bench=0&Dumbbell=0&EZBar=0&Kettlebell=0&MachineStrength=0&MachineCardio=0&Barbell=0&BodyOnly=0&ExerciseBall=0&FoamRoll=0&PullBar=0&WeightPlate=0&Other=0&Strength=0&Stretching=0&Powerlifting=0&OlympicWeightLifting=0&Beginner=0&Intermediate=0&Expert=0&page="
excercises_to_save(forearm_url, 6, "forearm_excercises")

glutes_url = "https://www.jefit.com/exercises/bodypart.php?id=5&exercises=Glutes&All=0&Bands=0&Bench=0&Dumbbell=0&EZBar=0&Kettlebell=0&MachineStrength=0&MachineCardio=0&Barbell=0&BodyOnly=0&ExerciseBall=0&FoamRoll=0&PullBar=0&WeightPlate=0&Other=0&Strength=0&Stretching=0&Powerlifting=0&OlympicWeightLifting=0&Beginner=0&Intermediate=0&Expert=0&page="
excercises_to_save(glutes_url, 3, "glutes_excercises")

shoulders_url = "https://www.jefit.com/exercises/bodypart.php?id=6&exercises=Shoulders&All=0&Bands=0&Bench=0&Dumbbell=0&EZBar=0&Kettlebell=0&MachineStrength=0&MachineCardio=0&Barbell=0&BodyOnly=0&ExerciseBall=0&FoamRoll=0&PullBar=0&WeightPlate=0&Other=0&Strength=0&Stretching=0&Powerlifting=0&OlympicWeightLifting=0&Beginner=0&Intermediate=0&Expert=0&page="
excercises_to_save(shoulders_url, 20, "shoulders_excercises")

triceps_url  = "https://www.jefit.com/exercises/bodypart.php?id=7&exercises=Triceps&All=0&Bands=0&Bench=0&Dumbbell=0&EZBar=0&Kettlebell=0&MachineStrength=0&MachineCardio=0&Barbell=0&BodyOnly=0&ExerciseBall=0&FoamRoll=0&PullBar=0&WeightPlate=0&Other=0&Strength=0&Stretching=0&Powerlifting=0&OlympicWeightLifting=0&Beginner=0&Intermediate=0&Expert=0&page="
excercises_to_save(triceps_url, 11, "triceps_excercises")

upper_legs_url = "https://www.jefit.com/exercises/bodypart.php?id=8&exercises=Upper-Legs&All=0&Bands=0&Bench=0&Dumbbell=0&EZBar=0&Kettlebell=0&MachineStrength=0&MachineCardio=0&Barbell=0&BodyOnly=0&ExerciseBall=0&FoamRoll=0&PullBar=0&WeightPlate=0&Other=0&Strength=0&Stretching=0&Powerlifting=0&OlympicWeightLifting=0&Beginner=0&Intermediate=0&Expert=0&page="
excercises_to_save(upper_legs_url, 18, "upper_legs_excercises")

lower_legs_url = "https://www.jefit.com/exercises/bodypart.php?id=9&exercises=Lower-Legs&All=0&Bands=0&Bench=0&Dumbbell=0&EZBar=0&Kettlebell=0&MachineStrength=0&MachineCardio=0&Barbell=0&BodyOnly=0&ExerciseBall=0&FoamRoll=0&PullBar=0&WeightPlate=0&Other=0&Strength=0&Stretching=0&Powerlifting=0&OlympicWeightLifting=0&Beginner=0&Intermediate=0&Expert=0&page="
excercises_to_save(lower_legs_url, 5, "lower_legs_excercises")

input('The work is done. Exit by ENTER')