# G2 50k interim checkpoint

This directory records an interim evaluation copied from the independent G2
two-A30 run at approximately 50,000/500,000 generations. It is retained only
for convergence auditing; the final candidate remains the running 500k model
on G2.

The 33-frame held-out metrics at this checkpoint are 0.01864 eV/atom energy
MAE, 0.27303 eV/A force MAE, and 0.05606 e BEC MAE (85 labelled atom rows).
The checkpoint was evaluated with the same official qNEP BTO architecture and
the unchanged 134/33 split. No labels were rewritten or shifted.
