"""Train comparable tabular regressors on the bundled legacy synthetic dataset."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib, platform, sklearn
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.ensemble import RandomForestRegressor, ExtraTreesRegressor, HistGradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import joblib, json
ROOT=Path(__file__).resolve().parents[1]
def train():
    p=ROOT/'data/raw/legacy_irrigation_dataset.csv'; df=pd.read_csv(p)
    target='water_need_mm'
    if target not in df: raise ValueError(f"Expected target column {target}; found {list(df.columns)}")
    X=df.drop(columns=[target]); y=df[target]
    cat=list(X.select_dtypes(include=['object']).columns); num=[c for c in X.columns if c not in cat]
    prep=ColumnTransformer([('cat',OneHotEncoder(handle_unknown='ignore'),cat),('num',StandardScaler(),num)])
    Xtr,Xte,ytr,yte=train_test_split(X,y,test_size=.2,random_state=42)
    models={'random_forest':RandomForestRegressor(n_estimators=250,random_state=42),'extra_trees':ExtraTreesRegressor(n_estimators=250,random_state=42),'hist_gradient':HistGradientBoostingRegressor(random_state=42)}
    results={}; best=None; best_mae=float('inf')
    for name,model in models.items():
        pipe=Pipeline([('prep',prep),('model',model)])
        pipe.fit(Xtr,ytr); pred=pipe.predict(Xte)
        mae=mean_absolute_error(yte,pred); rmse=mean_squared_error(yte,pred)**.5; r2=r2_score(yte,pred)
        results[name]={'MAE':mae,'RMSE':rmse,'R2':r2}
        if mae<best_mae: best_mae=mae; best=pipe
    models_dir = ROOT/'models'
    models_dir.mkdir(exist_ok=True)
    model_path = models_dir/'legacy_water_model.joblib'
    joblib.dump(best, model_path)
    dataset_hash = hashlib.sha256(p.read_bytes()).hexdigest()
    (models_dir/'metrics.json').write_text(json.dumps({
        'warning':'Bundled data is synthetic. Metrics do not establish field accuracy.',
        'evaluation':'Fixed 80/20 hold-out split with random_state=42; metrics describe synthetic data only.',
        'models':results,
    },indent=2), encoding='utf-8')
    (models_dir/'model_metadata.json').write_text(json.dumps({
        'artifact': model_path.name,
        'model_type': type(best.named_steps['model']).__name__,
        'trained_at_utc': datetime.now(timezone.utc).isoformat(),
        'python_version': platform.python_version(),
        'scikit_learn_version': sklearn.__version__,
        'joblib_version': joblib.__version__,
        'training_data': 'data/raw/legacy_irrigation_dataset.csv',
        'training_data_sha256': dataset_hash,
        'training_rows': int(len(Xtr)),
        'holdout_rows': int(len(Xte)),
        'target': target,
        'synthetic_data': True,
        'field_validated': False,
    }, indent=2), encoding='utf-8')
    return results
if __name__=='__main__': print(json.dumps(train(),indent=2))
