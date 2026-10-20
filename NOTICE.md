# Notices

BrowserForge-Stealth is licensed under the **GNU General Public License v3.0 only** (see `LICENSE`).

It contains work derived from the following Apache-2.0 licensed projects. Apache-2.0 is compatible with GPLv3, and
the original notices are preserved here. The full Apache-2.0 text is in `licenses/Apache-2.0.txt`.

* **browserforge** by daijro: https://github.com/daijro/browserforge. The Bayesian network engine
  (`bayesian_network.py`), the header generator (`headers/`) and the original fingerprint sampling logic
  (`sampler.py`) are derived from it.
* **fingerprint-suite** by Apify Technologies s.r.o.: https://github.com/apify/fingerprint-suite
  (Copyright 2018 Apify Technologies s.r.o.). `assets/utils.js.xz` is a compressed copy of its
  `fingerprint-injector/src/utils.js`, and the init-script template follows its injection logic.
* **apify-fingerprint-datapoints**: the Bayesian network data, installed as a dependency.
