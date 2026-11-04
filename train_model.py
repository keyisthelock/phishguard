"""Train a reproducible baseline. Spam is a proxy, not a phishing ground truth."""
import json
from pathlib import Path
import joblib
from sklearn.pipeline import Pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix
ROOT = Path(__file__).resolve().parent

def train():
    rows = []
    for line in (ROOT/'data/SMSSpamCollection').read_text(encoding='utf-8').splitlines():
        label, message = line.split('\t', 1)
        rows.append((message, int(label == 'spam')))
    # Deduplicate before splitting to prevent identical messages leaking into evaluation.
    rows = list(dict.fromkeys(rows))
    x, y = zip(*rows)
    a,b,c,d = train_test_split(x,y,test_size=.2,random_state=42,stratify=y)
    model = Pipeline([('tfidf', TfidfVectorizer(ngram_range=(1,2), sublinear_tf=True)), ('classifier', LogisticRegression(max_iter=1500, class_weight='balanced', random_state=42))])
    model.fit(a,c)
    report = {'dataset':'UCI SMS Spam Collection', 'limitation':'SMS spam labels are a proxy for scam detection; not a validated phishing benchmark. Probabilities are not calibrated safety guarantees.', 'unique_messages':len(rows),'training_messages':len(a),'test_messages':len(b),'random_state':42,'metrics':classification_report(d,model.predict(b),output_dict=True),'confusion_matrix':confusion_matrix(d,model.predict(b)).tolist()}
    (ROOT/'models').mkdir(exist_ok=True)
    joblib.dump(model, ROOT/'models/detector.joblib')
    (ROOT/'models/metrics.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))
if __name__ == '__main__': train()
