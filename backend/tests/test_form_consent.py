"""Формы ПДн и распознавание согласия."""

from app.compliance.form_consent import (
    _form_has_consent_checkbox,
    forms_missing_pdn_consent,
)
from bs4 import BeautifulSoup

OKNO_FEEDBACK_FORM = """
<form method="post">
  <input type="text" name="name"/>
  <input type="email" name="email"/>
  <input type="text" name="city"/>
  <p>Соглашаюсь с политикой конфиденциальности. Подробнее.</p>
  <input type="checkbox" name="accepts_the_licen" id="accepts_the_licen_Form"/>
  <button type="submit">Отправить</button>
</form>
"""


def test_okno_accepts_the_licen_checkbox():
    form = BeautifulSoup(OKNO_FEEDBACK_FORM, "html.parser").find("form")
    assert _form_has_consent_checkbox(form)
    assert not forms_missing_pdn_consent(OKNO_FEEDBACK_FORM)