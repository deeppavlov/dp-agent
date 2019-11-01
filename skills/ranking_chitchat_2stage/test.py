# %%
from deeppavlov import build_model

# %%
model = build_model("./agent_ranking_chitchat_2staged_tfidf_smn_v4_prep.json", download=True)


# %%
model(["hi"], [["hello"]])


# %%
