import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.svm import SVC
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, roc_auc_score, roc_curve
import pickle
import os

try:
    import shap
    SHAP_AVAILABLE = True
except ImportError:
    SHAP_AVAILABLE = False

# Page configuration
st.set_page_config(
    page_title="Emergency Triage AI",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom styling
st.markdown("""
    <style>
    .main {
        padding: 0rem 0rem;
    }
    </style>
""", unsafe_allow_html=True)

# Sidebar navigation
st.sidebar.title("🏥 Emergency Triage App")
page = st.sidebar.radio(
    "Select a section:",
    ["📊 Data Exploration", "🤖 Model Training", "🔮 Make Prediction", "📈 Model Performance"]
)

# Load data function
@st.cache_data
def load_data():
    try:
        df = pd.read_csv("data/emergency_traige1.csv")
        return df
    except FileNotFoundError:
        st.error("Data file not found!")
        return None

# Train model function
@st.cache_resource
def train_models(X_train, y_train):
    models = {}
    
    with st.spinner("Training Random Forest..."):
        rf_model = RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1)
        rf_model.fit(X_train, y_train)
        models['Random Forest'] = rf_model
    
    with st.spinner("Training SVM..."):
        svm_model = SVC(kernel='rbf', probability=True, random_state=42)
        svm_model.fit(X_train, y_train)
        models['SVM'] = svm_model
    
    return models

# ======================== PAGE: DATA EXPLORATION ========================
if page == "📊 Data Exploration":
    st.title("📊 Data Exploration")
    
    df = load_data()
    if df is not None:
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Records", len(df))
        with col2:
            st.metric("Total Features", df.shape[1])
        with col3:
            st.metric("Missing Values", df.isnull().sum().sum())
        
        st.subheader("Dataset Overview")
        st.dataframe(df.head(10), use_container_width=True)
        
        st.subheader("Data Statistics")
        st.dataframe(df.describe(), use_container_width=True)
        
        # Target variable distribution
        if 'KTAS_expert' in df.columns:
            st.subheader("Target Variable Distribution (KTAS Score)")
            col1, col2 = st.columns(2)
            
            with col1:
                fig, ax = plt.subplots(figsize=(8, 5))
                df['KTAS_expert'].value_counts().sort_index().plot(kind='bar', ax=ax, color='steelblue')
                ax.set_title("KTAS Score Distribution")
                ax.set_xlabel("KTAS Score")
                ax.set_ylabel("Count")
                st.pyplot(fig)
            
            with col2:
                fig, ax = plt.subplots(figsize=(8, 5))
                df['KTAS_expert'].value_counts().plot(kind='pie', ax=ax, autopct='%1.1f%%')
                ax.set_title("KTAS Score Percentage")
                ax.set_ylabel("")
                st.pyplot(fig)
        
        # Feature correlation heatmap
        st.subheader("Feature Correlation Heatmap")
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        
        if len(numeric_cols) > 1:
            fig, ax = plt.subplots(figsize=(12, 8))
            correlation = df[numeric_cols].corr()
            sns.heatmap(correlation, annot=False, cmap='coolwarm', ax=ax, square=True)
            ax.set_title("Correlation Matrix")
            st.pyplot(fig)
        
        # Missing values analysis
        st.subheader("Missing Values Analysis")
        missing = df.isnull().sum()
        if missing.sum() > 0:
            fig, ax = plt.subplots(figsize=(10, 5))
            missing[missing > 0].plot(kind='barh', ax=ax, color='coral')
            ax.set_title("Missing Values per Feature")
            ax.set_xlabel("Count")
            st.pyplot(fig)
        else:
            st.info("No missing values found in the dataset!")

# ======================== PAGE: MODEL TRAINING ========================
elif page == "🤖 Model Training":
    st.title("🤖 Model Training")
    
    df = load_data()
    if df is not None:
        st.subheader("Data Preparation")
        
        # Select target variable
        target_col = st.selectbox("Select Target Variable:", [col for col in df.columns if 'KTAS' in col or 'triage' in col.lower()])
        
        # Drop non-numeric columns and target
        X = df.drop(columns=[col for col in df.columns if col == target_col or df[col].dtype == 'object'])
        y = df[target_col]
        
        # Train-test split
        col1, col2, col3 = st.columns(3)
        with col1:
            test_size = st.slider("Test Set Size:", 0.1, 0.5, 0.2)
        with col2:
            random_state = st.number_input("Random State:", value=42)
        with col3:
            st.write("")  # Spacing
        
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=test_size, random_state=random_state)
        
        st.info(f"✅ Training set: {len(X_train)} samples | Test set: {len(X_test)} samples")
        
        # Train models
        st.subheader("🤖 Train Models")
        if st.button("Train Models Now", key="train_btn"):
            models = train_models(X_train, y_train)

            # Evaluate models
            st.subheader("Model Performance")
            results = {}
            for model_name, model in models.items():
                y_pred = model.predict(X_test)
                accuracy = accuracy_score(y_test, y_pred)
                results[model_name] = {
                    'accuracy': accuracy,
                    'model': model,
                    'predictions': y_pred
                }

            # Display results
            col1, col2 = st.columns(2)
            for idx, (model_name, result) in enumerate(results.items()):
                with (col1 if idx == 0 else col2):
                    st.metric(f"{model_name} Accuracy", f"{result['accuracy']:.2%}")

            # Feature importance for Random Forest
            if 'Random Forest' in results:
                st.subheader("📊 Random Forest Feature Importance")
                rf_model = results['Random Forest']['model']
                feature_importance = pd.DataFrame({
                    'Feature': X.columns,
                    'Importance': rf_model.feature_importances_
                }).sort_values('Importance', ascending=False).head(15)

                fig, ax = plt.subplots(figsize=(10, 6))
                ax.barh(feature_importance['Feature'], feature_importance['Importance'], color='steelblue')
                ax.set_xlabel("Importance")
                ax.set_title("Top 15 Important Features (Random Forest)")
                st.pyplot(fig)

            # Auto-save models immediately (avoids nested button rerun issue)
            os.makedirs("models", exist_ok=True)
            for model_name, result in results.items():
                model_path = f"models/{model_name.lower().replace(' ', '_')}_model.pkl"
                with open(model_path, 'wb') as f:
                    pickle.dump(result['model'], f)
            st.success("✅ Models trained and saved! Go to 'Make Prediction' to use them.")

# ======================== PAGE: MAKE PREDICTION ========================
elif page == "🔮 Make Prediction":
    st.title("🔮 Patient Symptom Assessment")

    # ── Backend CTAS config (patient never sees CTAS numbers) ──
    CTAS_CONFIG = {
        1: {
            "action": "Call 911 Now",
            "message": "This is a life-threatening emergency. Call 911 immediately. Do not drive yourself to the hospital.",
            "bg_color": "#FF0000", "text_color": "white",
            "border_color": "#8B0000", "emoji": "🚨", "full_alert": True,
        },
        2: {
            "action": "Go to Emergency Room",
            "message": "Your symptoms need prompt attention. Please head to the nearest Emergency Department within 15–30 minutes.",
            "bg_color": "#FFE5E5", "text_color": "#8B0000",
            "border_color": "#FF4500", "emoji": "🏥", "full_alert": False,
        },
        3: {
            "action": "Visit Urgent Care Today",
            "message": "Your symptoms should be evaluated soon. Visit an urgent care clinic or walk-in within the next few hours.",
            "bg_color": "#FFF3CD", "text_color": "#7D4E00",
            "border_color": "#FFA500", "emoji": "⚕️", "full_alert": False,
        },
        4: {
            "action": "See a Doctor Soon",
            "message": "Your symptoms don't appear to be an emergency, but you should see a doctor within the next day or two.",
            "bg_color": "#D4EDDA", "text_color": "#155724",
            "border_color": "#28A745", "emoji": "👨‍⚕️", "full_alert": False,
        },
        5: {
            "action": "Connect with a Doctor Online",
            "message": "Your symptoms appear manageable. You can book a telehealth appointment from home.",
            "bg_color": "#CCE5FF", "text_color": "#004085",
            "border_color": "#007BFF", "emoji": "💻", "full_alert": False,
        },
    }

    FEATURE_LABELS = {
        'Age': 'age', 'Sex': 'sex', 'HR': 'heart rate', 'RR': 'respiration rate',
        'BT': 'body temperature', 'SBP': 'systolic blood pressure',
        'DBP': 'diastolic blood pressure', 'Saturation': 'oxygen saturation',
        'NRS_pain': 'pain score', 'KTAS_RN': 'initial nurse assessment',
        'Pain': 'pain level', 'Mental': 'mental status', 'Injury': 'injury type',
        'Group': 'patient group',
    }

    # (low, high, unit)  — None means no defined range
    NORMAL_RANGES = {
        'HR':         (60,   100,  'bpm'),
        'RR':         (12,   20,   'breaths/min'),
        'BT':         (36.1, 37.2, '°C'),
        'SBP':        (90,   120,  'mmHg'),
        'DBP':        (60,   80,   'mmHg'),
        'Saturation': (95,   100,  '%'),
        'NRS_pain':   (0,    3,    '/10'),
    }

    df = load_data()
    if df is not None:
        st.subheader("Enter Patient Information")

        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        numeric_cols = [col for col in numeric_cols if 'KTAS' not in col]

        input_data = {}
        cols = st.columns(3)
        for idx, col_name in enumerate(numeric_cols):
            col = cols[idx % 3]
            input_data[col_name] = col.slider(
                f"{col_name}:",
                float(df[col_name].min()),
                float(df[col_name].max()),
                float(df[col_name].mean()),
                key=col_name,
            )

        input_df = pd.DataFrame([input_data])

        with st.expander("View Patient Data Summary"):
            st.dataframe(input_df, use_container_width=True)

        st.subheader("Get Recommendation")
        model_files = {
            'Random Forest': 'models/random_forest_model.pkl',
            'SVM': 'models/svm_model.pkl',
        }
        selected_model = st.selectbox("Select Model:", list(model_files.keys()))

        if st.button("Get Recommendation", key="predict_btn"):
            model_path = model_files[selected_model]

            if not os.path.exists(model_path):
                st.error("❌ Model not found. Please train models first in the 'Model Training' section.")
            else:
                with open(model_path, 'rb') as f:
                    model = pickle.load(f)

                prediction = model.predict(input_df)[0]

                # ── Section 1: Color-coded Recommendation Card ──
                if prediction in CTAS_CONFIG:
                    cfg = CTAS_CONFIG[prediction]

                    if cfg["full_alert"]:
                        # CTAS 1 — full-screen red with 911 call button
                        st.markdown(f"""
                        <div style="
                            background: linear-gradient(135deg, #CC0000, #8B0000);
                            padding: 3rem 2rem; border-radius: 16px;
                            text-align: center; margin: 1rem 0;
                            box-shadow: 0 8px 32px rgba(204,0,0,0.5);
                        ">
                            <div style="font-size: 4rem; margin-bottom: 0.5rem;">🚨</div>
                            <h1 style="color:white; font-size:2.8rem; margin:0 0 1rem 0; font-weight:900; letter-spacing:2px;">
                                {cfg['action']}
                            </h1>
                            <p style="color:#FFD0D0; font-size:1.2rem; margin:0 auto 2rem auto; max-width:560px; line-height:1.6;">
                                {cfg['message']}
                            </p>
                            <a href="tel:911" style="
                                background:white; color:#CC0000;
                                padding:1rem 3.5rem; border-radius:50px;
                                font-size:1.8rem; font-weight:900;
                                text-decoration:none; display:inline-block;
                                box-shadow:0 4px 20px rgba(0,0,0,0.35);
                                letter-spacing:3px;
                            ">📞 CALL 911</a>
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.markdown(f"""
                        <div style="
                            background-color:{cfg['bg_color']};
                            border-left:8px solid {cfg['border_color']};
                            padding:2rem; border-radius:12px; margin:1rem 0;
                            box-shadow:0 4px 12px rgba(0,0,0,0.08);
                        ">
                            <h2 style="color:{cfg['text_color']}; font-size:2rem; margin:0 0 0.75rem 0;">
                                {cfg['emoji']} {cfg['action']}
                            </h2>
                            <p style="color:{cfg['text_color']}; font-size:1.1rem; margin:0; line-height:1.6;">
                                {cfg['message']}
                            </p>
                        </div>
                        """, unsafe_allow_html=True)

                # ── Section 2: SHAP Explanation ──
                st.markdown("---")
                st.subheader("Why We're Recommending This")
                st.write("We're recommending this because:")

                explanation_items = []  # list of (sentence, is_concerning)

                if SHAP_AVAILABLE and selected_model == 'Random Forest':
                    try:
                        X_bg = df[numeric_cols].dropna().sample(min(100, len(df)), random_state=42)
                        explainer = shap.TreeExplainer(model)
                        shap_vals = explainer.shap_values(input_df[numeric_cols])

                        # Use SHAP for KTAS=1 class to define urgency direction
                        classes = list(model.classes_)
                        urgent_idx = classes.index(1) if 1 in classes else 0
                        urgency_shap = shap_vals[urgent_idx][0]  # shape: (n_features,)

                        top_idx = np.argsort(np.abs(urgency_shap))[::-1][:8]

                        for i in top_idx:
                            feat = numeric_cols[i]
                            val = input_data[feat]
                            shap_v = urgency_shap[i]
                            is_concerning = shap_v > 0  # positive = pushes toward KTAS 1 (urgent)

                            label = FEATURE_LABELS.get(feat, feat)

                            if feat in NORMAL_RANGES:
                                lo, hi, unit = NORMAL_RANGES[feat]
                                val_str = f"{val:.1f} {unit}"
                                if val < lo:
                                    context = f"is below the normal range of {lo}–{hi} {unit}"
                                elif val > hi:
                                    context = f"is above the normal range of {lo}–{hi} {unit}"
                                else:
                                    context = f"is within the normal range of {lo}–{hi} {unit}"
                            else:
                                val_str = f"{val:.1f}"
                                context = "was recorded"

                            note = "— this raises concern" if is_concerning else "— this is a reassuring sign"
                            sentence = f"Your {label} ({val_str}) {context} {note}"
                            explanation_items.append((sentence, is_concerning))

                    except Exception as e:
                        st.warning(f"SHAP calculation failed: {e}. Showing value-based analysis.")

                # Fallback: normal-range based explanation (also used if SHAP failed)
                if not explanation_items:
                    raw = []
                    for feat, val in input_data.items():
                        if feat in NORMAL_RANGES:
                            lo, hi, unit = NORMAL_RANGES[feat]
                            val_str = f"{val:.1f} {unit}"
                            if val < lo:
                                raw.append((abs(val - lo), feat, val_str,
                                            f"is below the normal range of {lo}–{hi} {unit}", True))
                            elif val > hi:
                                raw.append((abs(val - hi), feat, val_str,
                                            f"is above the normal range of {lo}–{hi} {unit}", True))
                            else:
                                raw.append((0, feat, val_str,
                                            f"is within the normal range of {lo}–{hi} {unit}", False))

                    raw.sort(key=lambda x: x[0], reverse=True)
                    for _, feat, val_str, context, is_concerning in raw[:8]:
                        label = FEATURE_LABELS.get(feat, feat)
                        note = "— this raises concern" if is_concerning else "— this is a reassuring sign"
                        explanation_items.append((f"Your {label} ({val_str}) {context} {note}", is_concerning))

                # Render explanation items
                for sentence, is_concerning in explanation_items:
                    color = "#CC0000" if is_concerning else "#155724"
                    bg = "#FFF0F0" if is_concerning else "#F0FFF4"
                    dot = "🔴" if is_concerning else "🟢"
                    st.markdown(f"""
                    <div style="
                        background:{bg}; border-left:4px solid {color};
                        padding:0.65rem 1rem; margin:0.35rem 0; border-radius:6px;
                    ">
                        {dot} <span style="color:{color}; font-size:0.97rem;">{sentence}</span>
                    </div>
                    """, unsafe_allow_html=True)

# ======================== PAGE: MODEL PERFORMANCE ========================
elif page == "📈 Model Performance":
    st.title("📈 Model Performance Metrics")

    df = load_data()
    if df is not None:
        target_col = [col for col in df.columns if 'KTAS' in col or 'triage' in col.lower()][0]
        X = df.drop(columns=[col for col in df.columns if col == target_col or df[col].dtype == 'object'])
        y = df[target_col]

        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        models = train_models(X_train, y_train)

        st.subheader("Detailed Model Evaluation")
        for model_name, model in models.items():
            with st.expander(f"📊 {model_name} Details", expanded=True):
                y_pred = model.predict(X_test)

                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Accuracy", f"{accuracy_score(y_test, y_pred):.4f}")
                with col2:
                    st.metric("Samples Tested", len(X_test))
                with col3:
                    st.metric("Classes", len(np.unique(y_test)))

                fig, ax = plt.subplots(figsize=(8, 6))
                cm = confusion_matrix(y_test, y_pred)
                sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', ax=ax)
                ax.set_title(f"{model_name} - Confusion Matrix")
                ax.set_ylabel("True Label")
                ax.set_xlabel("Predicted Label")
                st.pyplot(fig)

                st.subheader("Classification Report")
                report = classification_report(y_test, y_pred, output_dict=True)
                report_df = pd.DataFrame(report).transpose()
                st.dataframe(report_df, use_container_width=True)

st.sidebar.markdown("---")
st.sidebar.info("🏥 This AI system assists in emergency triage prioritization using machine learning.")
