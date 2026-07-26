import os
import joblib
import numpy as np

BASE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_MODEL = os.path.join(BASE, 'xgboost_model.pkl')


class RiderBrain:
    """
    Wrapper around the trained XGBoost surrogate model.
    Exposes a single clean decision interface to the simulator:
    given the conditions of an offer, it returns accept/reject.
    """

    def __init__(self, model_path=DEFAULT_MODEL):
        bundle = joblib.load(model_path)
        self.model = bundle['model']
        self.features = bundle['features']   # feature order was saved with the model

    def _vector(self, incentive, distance, weather_bad, urgency_high):
        # Build the feature vector IN THE ORDER the model expects,
        # not a hardcoded order — so if training changes, this won't silently break.
        values = {
            'Distance_m': distance,
            'Incentive_Euro': incentive,
            'Weather_Bad': int(weather_bad),
            'Urgency_High': int(urgency_high),
        }
        return np.array([[values[f] for f in self.features]])

    def accept_probability(self, incentive, distance, weather_bad=0, urgency_high=0):
        """Return the acceptance probability (0..1)."""
        x = self._vector(incentive, distance, weather_bad, urgency_high)
        return float(self.model.predict_proba(x)[0][1])

    def decide(self, incentive, distance, weather_bad=0, urgency_high=0):
        """Return True (accept) / False (reject)."""
        x = self._vector(incentive, distance, weather_bad, urgency_high)
        return bool(self.model.predict(x)[0])


if __name__ == "__main__":
    brain = RiderBrain()
    print("Features:", brain.features)

    # Sanity checks — obvious cases
    tests = [
        # (incentive, distance, weather, urgency, expected)
        (5.0, 100, 0, 0, "ACCEPT — high reward, close, ideal conditions"),
        (0.5, 550, 1, 1, "REJECT — tiny reward, far, rain, in a hurry"),
        (3.0, 250, 0, 0, "borderline"),
        (5.0, 550, 0, 0, "REJECT? — good reward but beyond the walk cliff"),
    ]
    for inc, dist, w, u, note in tests:
        p = brain.accept_probability(inc, dist, w, u)
        d = brain.decide(inc, dist, w, u)
        print(f"EUR {inc:<4} {dist:>4}m w={w} u={u} -> P={p:.2f} decide={d}  ({note})")