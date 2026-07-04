"""
backend/ml/

ML training and inference modules for UrbanPulse.

Contains:
  - train_city_recommender.py        : RandomForestClassifier — predicts
                                        the most likely city a user would
                                        select, given their profile.
  - train_salary_equivalence_model.py: GradientBoostingRegressor — predicts
                                        the salary required in a target
                                        city for equivalent purchasing
                                        power to a source-city salary.
  - feature_importance.py            : Loads both trained models and
                                        exports feature importance rankings.
"""