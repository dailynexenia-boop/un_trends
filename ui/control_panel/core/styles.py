import streamlit as st

def apply_styles():
    st.markdown(
        """
<style>
/* Base */
.block-container { padding-top: 1.8rem; padding-bottom: 2rem; max-width: 1280px; }
h1, h2, h3 { letter-spacing: 0.2px; margin-bottom: 0.35rem; }
p { line-height: 1.45; }
small { opacity: 0.75; }

/* Sidebar */
section[data-testid="stSidebar"] { border-right: 1px solid rgba(255,255,255,0.06); }
section[data-testid="stSidebar"] .block-container { padding-top: 1.25rem; }
.sidebar-title { font-size: 1.05rem; font-weight: 650; margin-bottom: 0.6rem; }
.sidebar-sub { font-size: 0.9rem; opacity: 0.75; margin-bottom: 1rem; }

/* Cards */
.card {
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 16px;
  padding: 16px 16px;
  background: rgba(255,255,255,0.03);
}
.card + .card { margin-top: 12px; }

.section-card {
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 18px;
  padding: 18px 18px;
  background: rgba(255,255,255,0.03);
  margin: 14px 0 18px 0;
}

.card-title { font-weight: 700; font-size: 1.0rem; margin-bottom: 6px; }
.card-desc { opacity: 0.78; font-size: 0.93rem; margin-bottom: 12px; }

.card-current { font-size: 0.86rem; opacity: 0.70; margin-top: 6px; }
.card-value { font-size: 1.05rem; font-weight: 650; margin-top: 2px; }

.card-help { font-size: 0.90rem; opacity: 0.75; margin-top: 10px; }

.btn-row { margin-top: 12px; }

.kpi-row { display:flex; gap: 10px; margin-top: 12px; flex-wrap: wrap; }
.kpi {
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 999px;
  padding: 6px 10px;
  background: rgba(255,255,255,0.03);
  font-size: 0.84rem;
  opacity: 0.85;
}

/* Inputs */
label { opacity: 0.85; }
div[data-baseweb="input"] input, textarea {
  border-radius: 12px !important;
}

/* Divider */
.hr { height: 1px; background: rgba(255,255,255,0.08); margin: 14px 0; }

/* Remove Streamlit default padding in some places */
div[data-testid="stVerticalBlock"] > div:has(> .card) { padding-top: 0.2rem; }

/* Make buttons look more “product” */
.stButton > button {
  border-radius: 12px;
  padding: 0.55rem 0.85rem;
  border: 1px solid rgba(255,255,255,0.12);
}
</style>
""",
        unsafe_allow_html=True,
    )
