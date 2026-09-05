"""
Shared "train all the models, compare, keep the best" step.

Trains three explainable classifiers on the final (post-selection) feature
set -- a shallow Decision Tree (readable if/else rules, good for a judge
Q&A), Logistic Regression (linear coefficients = feature weights), and a
linear SVM (margin-based, coefficients also readable) -- plus an RBF-kernel
SVM as a non-linear accuracy ceiling for comparison only. Saves every model
with joblib and picks the best by F1 on the minority/positive class.
"""

import json

import joblib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    confusion_matrix, classification_report,
)
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC
from sklearn.tree import DecisionTreeClassifier, export_text, plot_tree

RANDOM_STATE = 42


def _eval(y_test, y_pred, pos_label):
    return {
        "accuracy": accuracy_score(y_test, y_pred),
        "precision": precision_score(y_test, y_pred, pos_label=pos_label, zero_division=0),
        "recall": recall_score(y_test, y_pred, pos_label=pos_label, zero_division=0),
        "f1": f1_score(y_test, y_pred, pos_label=pos_label, zero_division=0),
    }


def train_and_compare(
    X: pd.DataFrame,
    y: pd.Series,
    out_prefix: str,
    results_dir,
    pos_label=1,
    test_size: float = 0.25,
    max_depth: int = 4,
) -> dict:
    """Trains DecisionTree / LogisticRegression / LinearSVM / RBF-SVM on
    (X, y), saves each model + a comparison report under
    ``results_dir/<out_prefix>_*``, and returns a metrics summary dict.
    """
    results_dir = str(results_dir)
    feature_names = list(X.columns)
    stratify = y if y.value_counts().min() >= 2 else None
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=RANDOM_STATE, stratify=stratify,
    )

    scaler = StandardScaler().fit(X_train)
    X_train_s = scaler.transform(X_train)
    X_test_s = scaler.transform(X_test)

    models = {
        "decision_tree": DecisionTreeClassifier(
            max_depth=max_depth, class_weight="balanced", random_state=RANDOM_STATE,
        ),
        "logistic_regression": LogisticRegression(
            max_iter=2000, class_weight="balanced", random_state=RANDOM_STATE,
        ),
        "svm_linear": SVC(
            kernel="linear", class_weight="balanced", probability=True, random_state=RANDOM_STATE,
        ),
        "svm_rbf": SVC(
            kernel="rbf", class_weight="balanced", probability=True, random_state=RANDOM_STATE,
        ),
    }

    metrics = {}
    for name, clf in models.items():
        if name == "decision_tree":
            clf.fit(X_train, y_train)
            y_pred = clf.predict(X_test)
        else:
            clf.fit(X_train_s, y_train)
            y_pred = clf.predict(X_test_s)

        m = _eval(y_test, y_pred, pos_label)
        m["confusion_matrix"] = confusion_matrix(y_test, y_pred).tolist()
        m["classification_report"] = classification_report(y_test, y_pred, zero_division=0)
        metrics[name] = m

        model_path = f"{results_dir}/{out_prefix}_{name}.joblib"
        joblib.dump({"model": clf, "scaler": None if name == "decision_tree" else scaler,
                     "feature_names": feature_names}, model_path)

    best_name = max(metrics, key=lambda n: metrics[n]["f1"])

    # explainability artifacts for the decision tree (the pitch-facing model)
    tree = models["decision_tree"]
    rules_text = export_text(tree, feature_names=feature_names)
    with open(f"{results_dir}/{out_prefix}_tree_rules.txt", "w") as f:
        f.write(rules_text)

    plt.figure(figsize=(16, 8))
    plot_tree(tree, feature_names=feature_names, class_names=[str(c) for c in tree.classes_],
              filled=True, rounded=True, fontsize=9)
    plt.tight_layout()
    plt.savefig(f"{results_dir}/{out_prefix}_tree.png", dpi=150)
    plt.close()

    report = {
        "out_prefix": out_prefix,
        "n_features": len(feature_names),
        "features": feature_names,
        "n_train": len(X_train),
        "n_test": len(X_test),
        "best_model": best_name,
        "metrics": {n: {k: v for k, v in m.items() if k != "classification_report"} for n, m in metrics.items()},
    }
    with open(f"{results_dir}/{out_prefix}_report.json", "w") as f:
        json.dump(report, f, indent=2, default=str)

    print(f"\n=== {out_prefix}: model comparison ===")
    print(pd.DataFrame({n: {k: v for k, v in m.items() if k in ("accuracy", "precision", "recall", "f1")}
                         for n, m in metrics.items()}).T.round(3))
    print(f"Best model: {best_name} (by F1)")
    print(f"\n=== {out_prefix}: decision tree rules ===")
    print(rules_text)

    return report
