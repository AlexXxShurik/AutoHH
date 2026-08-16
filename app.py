from app.apply import apply_to_all, load_cover_letter
from app.auth import ensure_logged_in
from app.driver import create_driver
from app.vacancies import fetch_all_vacancies


def main() -> None:
    driver = create_driver()
    try:
        ensure_logged_in(driver)
        while True:
            vacancies = fetch_all_vacancies(driver)
            print(f"\nВсего подходящих вакансий: {len(vacancies)}", flush=True)
            for vacancy in vacancies:
                print(vacancy)

            while True:
                answer = input("Откликнуться на вакансии? [да/нет/заново]: ").strip().lower()
                if answer in ("нет", "н", "no"):
                    return
                if answer in ("заново", "з"):
                    break
                if answer in ("да", "д", "yes"):
                    letter = load_cover_letter()
                    apply_to_all(driver, vacancies, letter)
                    return
                print("Не понял ответ. Введите: да / нет / заново", flush=True)
    finally:
        driver.quit()


if __name__ == "__main__":
    main()