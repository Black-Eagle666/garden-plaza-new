"""Тести SEO-частини сторінок закладів:  python3 -m unittest discover -s tools"""
import unittest

import zaklady_seo as seo


def place(**over):
    base = {"slug": "nova-kramnytsia", "name": "Нова крамниця", "cat_code": "shop", "floor": 2,
            "hours": "", "phones": [], "about": ""}
    return {**base, **over}


class CleanNameTest(unittest.TestCase):
    def test_strips_trailing_dot_left_by_owner(self):
        self.assertEqual(seo.clean_name("Килимовий дім."), "Килимовий дім")

    def test_keeps_name_without_dot_untouched(self):
        self.assertEqual(seo.clean_name("GYM MAXI"), "GYM MAXI")


class PlainTextTest(unittest.TestCase):
    def test_removes_emoji_and_joins_lines_into_sentences(self):
        raw = "KYLYMOVYY DIM — затишок починається з деталей 🖤\nУ нас широкий вибір:\n✨ Килими\n✨ Лінолеум\nДопоможемо підібрати"
        self.assertEqual(seo.plain_text(raw),
                         "KYLYMOVYY DIM — затишок починається з деталей. У нас широкий вибір: килими, лінолеум. Допоможемо підібрати.")

    def test_single_line_text_gets_only_final_dot(self):
        self.assertEqual(seo.plain_text("Салон штор: тюль і карнизи"), "Салон штор: тюль і карнизи.")

    def test_empty_text_stays_empty(self):
        self.assertEqual(seo.plain_text("  \n "), "")


class KindTest(unittest.TestCase):
    def test_known_slug_gets_its_own_kind_and_schema_type(self):
        kind = seo.kind_of(place(slug="apteka", cat_code="services"))
        self.assertEqual((kind["kind"], kind["schema"]), ("аптека", "Pharmacy"))

    def test_unknown_slug_falls_back_to_category(self):
        kind = seo.kind_of(place(cat_code="grocery"))
        self.assertEqual((kind["kind"], kind["schema"]), ("продуктовий магазин", "GroceryStore"))

    def test_unknown_category_falls_back_to_plain_shop(self):
        self.assertEqual(seo.kind_of(place(cat_code="щось нове"))["kind"], "магазин")


class TitleTest(unittest.TestCase):
    def test_title_says_what_the_place_is_and_where(self):
        title = seo.seo_title(place(slug="la-butik", name="La Butik", cat_code="fashion"))
        self.assertEqual(title, "La Butik — магазин взуття в Нересниці | ТЦ Garden Plaza New")

    def test_name_that_already_says_what_it_is_is_not_repeated(self):
        title = seo.seo_title(place(slug="apteka", name="Аптека Подорожник"))
        self.assertEqual(title, "Аптека Подорожник у Нересниці | ТЦ Garden Plaza New")

    def test_long_title_uses_short_mall_name(self):
        title = seo.seo_title(place(slug="furt-servis", name="Furt Service."))
        self.assertEqual(title, "Furt Service — ремонт телефонів і ноутбуків у Нересниці | ТЦ Garden Plaza")


class IntroTest(unittest.TestCase):
    def test_intro_names_kind_village_floor_and_address(self):
        text = seo.intro(place(slug="alma", name="ALMA", floor=1))
        self.assertEqual(text, "ALMA — супермаркет у Нересниці. Шукайте на 1 поверсі ТЦ Garden Plaza New (Гарден Плаза): "
                               "вул. Грушевського, 30, Тячівський район, Закарпаття.")


class DescriptionTest(unittest.TestCase):
    def test_description_fits_search_snippet_and_keeps_address(self):
        text = seo.seo_description(place(slug="shtory", name="IMPERIA GARDIN", hours="10:00–19:00",
                                         about="Салон штор IMPERIA GARDIN: штори, тюль, римські й рулонні штори, карнизи, "
                                               "декоративні подушки. Понад 300 тканин у наявності, пошиття за вашими розмірами."))
        self.assertLessEqual(len(text), seo.DESCRIPTION_MAX)
        self.assertTrue(text.endswith("2 поверх ТЦ Garden Plaza New, Нересниця. Графік: 10:00–19:00."))

    def test_empty_about_is_replaced_by_kind_sentence(self):
        text = seo.seo_description(place(slug="la-butik", name="La Butik"))
        self.assertTrue(text.startswith("La Butik — магазин взуття в Нересниці."))


class HoursTest(unittest.TestCase):
    ALL = list(seo.WEEK)

    def test_time_without_days_means_every_day(self):
        self.assertEqual(seo.parse_hours("9:00-19:30"), [{"days": self.ALL, "opens": "09:00", "closes": "19:30"}])

    def test_every_day_with_space_instead_of_dash(self):
        self.assertEqual(seo.parse_hours("Щодня 9:00 18:00"), [{"days": self.ALL, "opens": "09:00", "closes": "18:00"}])

    def test_two_groups_of_days(self):
        self.assertEqual(seo.parse_hours("Пн–Сб 8:00–21:00, Нд 9:00–21:00"), [
            {"days": self.ALL[:6], "opens": "08:00", "closes": "21:00"},
            {"days": ["Sunday"], "opens": "09:00", "closes": "21:00"}])

    def test_two_groups_without_comma(self):
        self.assertEqual(seo.parse_hours("Пн-Сб 09:00 - 17:00 Нд 10:00 - 17:00"), [
            {"days": self.ALL[:6], "opens": "09:00", "closes": "17:00"},
            {"days": ["Sunday"], "opens": "10:00", "closes": "17:00"}])

    def test_days_written_in_words(self):
        self.assertEqual(seo.parse_hours("З понеділка по суботу з 09:00-19:00"),
                         [{"days": self.ALL[:6], "opens": "09:00", "closes": "19:00"}])

    def test_words_between_days_and_time(self):
        self.assertEqual(seo.parse_hours("Пн-Сб, з 9:00 по 19:00"),
                         [{"days": self.ALL[:6], "opens": "09:00", "closes": "19:00"}])

    def test_day_off_is_left_out(self):
        self.assertEqual(seo.parse_hours("Пн–Сб 9:00–18:00, Нд вихідний"),
                         [{"days": self.ALL[:6], "opens": "09:00", "closes": "18:00"}])

    def test_closing_after_midnight_is_kept(self):
        self.assertEqual(seo.parse_hours("7:00–01:00"), [{"days": self.ALL, "opens": "07:00", "closes": "01:00"}])

    def test_round_the_clock(self):
        self.assertEqual(seo.parse_hours("цілодобово"), [{"days": self.ALL, "opens": "00:00", "closes": "23:59"}])

    def test_text_without_time_gives_nothing(self):
        self.assertEqual(seo.parse_hours("уточнюйте в салоні"), [])
        self.assertEqual(seo.parse_hours(""), [])

    def test_day_off_named_after_hours_is_removed(self):
        self.assertEqual(seo.parse_hours("Працюємо з 9:00 до 18:00, у неділю вихідний"),
                         [{"days": self.ALL[:6], "opens": "09:00", "closes": "18:00"}])

    def test_unclear_schedule_gives_nothing_rather_than_wrong_hours(self):
        for text in ("9:00-18:00 Пн-Пт", "Вихідний: Нд. Пн–Сб 9:00–19:00", "Вихідний — неділя. 9:00-18:00",
                     "Пн-Пт 9:00-18:00, перерва 13:00-14:00", "Пн-Пт 9:00-18:00, обід 13:00-14:00",
                     "Пн-Пт з 9:00, Сб з 10:00 до 14:00", "щодня 9:00-21:00, Нд до 15:00",
                     "Щодня 9:00–21:00, у вівторок 9:00-15:00"):
            self.assertEqual(seo.parse_hours(text), [], text)

    def test_impossible_time_gives_nothing(self):
        self.assertEqual(seo.parse_hours("9:00–29:00"), [])


class PhoneTest(unittest.TestCase):
    def test_placeholder_number_is_not_real(self):
        self.assertFalse(seo.is_real_phone("0680000205"))

    def test_normal_and_free_numbers_are_real(self):
        self.assertTrue(seo.is_real_phone("0683477707"))
        self.assertTrue(seo.is_real_phone("0800212338"))


class SchemaTest(unittest.TestCase):
    def test_business_has_type_hours_and_no_placeholder_phone(self):
        data = seo.business_schema(
            place(slug="kredo-klinika", name="КредоКлінік", hours="Пн–Сб 8:00–19:00", phones=["0680000205"], links=[], logo=None),
            "Клініка.", "https://tcgardenplaza.com.ua/zaklady/kredo-klinika/", ["https://tcgardenplaza.com.ua/og.jpg"])
        self.assertEqual(data["@type"], "MedicalClinic")
        self.assertNotIn("telephone", data)
        self.assertEqual(data["openingHoursSpecification"][0]["opens"], "08:00")
        self.assertEqual(data["containedInPlace"]["@id"], "https://tcgardenplaza.com.ua/#mall")

    def test_business_without_own_hours_does_not_claim_any(self):
        data = seo.business_schema(place(links=[], logo=None), "Магазин.", "https://tcgardenplaza.com.ua/zaklady/x/", [])
        self.assertNotIn("openingHoursSpecification", data)


if __name__ == "__main__":
    unittest.main()
