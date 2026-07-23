with open("gpr_to_sop_mlcp.py") as f:
    content = f.read()

old = '''def predict_gpr_from_npz(npz_file, X_query, length_scale=None, noise=None):
    data = np.load(npz_file, allow_pickle=True)
    W_opt = data["W_opt"]'''

new = '''def predict_gpr_from_npz(npz_file, X_query, length_scale=None, noise=None):
    data = np.load(npz_file, allow_pickle=True)
    # Auto-detect sklearn model: if no W_opt key, load the .joblib model instead
    if "W_opt" not in data:
        import joblib, os
        model_file = npz_file.replace(".npz", ".joblib")
        if not os.path.exists(model_file):
            raise FileNotFoundError(f"sklearn model not found: {model_file}")
        gpr = joblib.load(model_file)
        return gpr.predict(X_query)
    W_opt = data["W_opt"]'''

if old in content:
    content = content.replace(old, new)
    with open("gpr_to_sop_mlcp.py", "w") as f:
        f.write(content)
    print("Patched successfully")
else:
    print("ERROR: old string not found exactly")
