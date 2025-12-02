import streamlit as st
from pages.login import login
from pages.logout import logout
from pages.page_1 import page_1
from pages.page_2 import page_2
from pages.page_3 import page_3

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

login_page = st.Page(login, title="Log in", icon=":material/login:")
logout_page = st.Page(logout, title="Log out", icon=":material/logout:")

page_1_page = st.Page(
    page_1,
    title="Page 1",
    icon=":material/dashboard:",
    default=True,
)

page_2_page = st.Page(
    page_2,
    title="Page 2",
    icon=":material/compress:",
)

page_3_page = st.Page(
    page_3,
    title="Page 3",
    icon=":material/swap_horiz:",
)

if st.session_state.logged_in:

    pg = st.navigation(
        {
            "Account": [logout_page],
            "Section 1": [page_1_page, page_2_page],
            "Section 2": [page_3_page],
        },
    )

else:
    pg = st.navigation([login_page])

pg.run()