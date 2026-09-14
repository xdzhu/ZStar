# G2 100k interim checkpoint

This directory records the independent G2 run at approximately 101,000/500,000
generations. It is an interim convergence audit, not the final model.

Held-out metrics on the fixed 33-frame test split are 0.01627 eV/atom energy
MAE, 0.28881 eV/A force MAE, and 0.10216 e BEC MAE (85 labelled atom rows).
The force and BEC values do not improve over the 5k four-GPU timing candidate
or the G1 100k audit, so no separate 100k phonon promotion is made. The G2
process continues toward the user-requested 500k endpoint.
