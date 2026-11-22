from app.compliance.form_consent import forms_with_weak_pdn_consent

WEAK = """
<form method="post" action="/send">
  <input type="text" name="name"/>
  <input type="email" name="email"/>
  <label><input type="checkbox" name="agree" id="agree"/> Согласен</label>
  <button type="submit">OK</button>
</form>
"""

STRONG = """
<form method="post">
  <input type="text" name="name"/>
  <input type="email" name="email"/>
  <label><input type="checkbox" name="accept" id="accept"/>
  Согласен на обработку персональных данных по политике</label>
  <button type="submit">OK</button>
</form>
"""


def test_weak_consent_detected():
    assert forms_with_weak_pdn_consent(WEAK)


def test_adequate_consent_not_weak():
    assert not forms_with_weak_pdn_consent(STRONG)