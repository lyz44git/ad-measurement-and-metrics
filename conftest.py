# Load scikit-learn's OpenMP runtime before LightGBM: on some macOS installs the two runtimes conflict and crash
# when LightGBM is imported first.
import sklearn.ensemble  # noqa: F401
