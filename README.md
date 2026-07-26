# Cloud Resource Allocation Multi-Agent System

A Multi-Agent System (MAS) for fair and efficient cloud resource allocation developed as part of a Master's research project in Computer Science at **Cheikh Anta Diop University (UCAD), Senegal**.

The proposed system combines **HRRN (Highest Response Ratio Next)** scheduling with **topological sorting** to improve fairness between client requests while efficiently managing task dependencies in a cloud computing environment.

This repository contains the implementation, dashboard, configuration files, and performance evaluation used during the research work.

---

## Table of Contents

- [Features](#features)
- [System Architecture](#system-architecture)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Project Structure](#project-structure)
- [Algorithms](#algorithms)
- [Experimental Results](#experimental-results)
- [Related Publication](#related-publication)
- [Citation](#citation)
- [Author](#author)
- [License](#license)

---

## Features

- Multi-Agent System (MAS) architecture
- Fair resource allocation using HRRN scheduling
- Dependency management through topological sorting
- Distributed resource management
- Real-time monitoring dashboard
- Configurable simulation parameters
- Performance evaluation and scalability analysis

---

## System Architecture

The system is composed of four collaborative software agents:

1. **ClientManagerAgent (CMA)**  
   Receives client requests, manages waiting queues and computes priorities using the HRRN scheduling algorithm.

2. **ResourceManagerAgent (RMA)**  
   Allocates cloud resources while respecting task dependencies using topological sorting.

3. **LoadBalancerAgent (LBA)**  
   Balances workloads across available resources to improve system utilization.

4. **MonitorAgent (MA)**  
   Continuously monitors system performance and collects execution metrics.

> *(Insert your architecture diagram here)*

```text
images/Architecture.png
```

---

## Installation

### Requirements

- Python 3.9 or later
- SPADE framework
- Prosody (or another XMPP server)
- Dependencies listed in `requirements.txt`

Clone the repository:

```bash
git clone https://github.com/Queen746/cloud-resource-allocation-multi-agent-system.git
cd cloud-resource-allocation-multi-agent-system
```

Install dependencies:

```bash
pip install -r requirements.txt
```

---

## Configuration

Create a configuration file named `config.yaml`.

Example:

```yaml
xmpp_server: "localhost"
xmpp_domain: "localhost"
xmpp_password: "password"

simulation_duration: 300

vip_clients: 5
standard_clients: 20

resource_config:
  available_cpu: 100
  available_memory: 256
  available_storage: 1000
```

Additional parameters can be customized according to the desired simulation scenario.

---

## Usage

Start the monitoring dashboard:

```bash
python dashboard/app.py
```

Run the simulation:

```bash
python run_simulation.py config.yaml
```

Open your browser at:

```
http://localhost:5000
```

---

## Project Structure

```
cloud-resource-allocation-multi-agent-system/
│
├── agents/
│   ├── client_manager_agent.py
│   ├── resource_manager_agent.py
│   ├── load_balancer_agent.py
│   └── monitor_agent.py
│
├── dashboard/
│
├── models/
│
├── tests/
│
├── utils/
│
├── config/
│
├── requirements.txt
├── README.md
├── LICENSE
└── CITATION.cff
```

---

## Algorithms

### Highest Response Ratio Next (HRRN)

The HRRN scheduling policy computes the priority of each request according to:

```
Priority = (Waiting Time + Estimated Execution Time)
           / Estimated Execution Time
```

This strategy naturally increases the priority of requests that have waited longer, reducing starvation while maintaining fairness.

---

### Topological Sorting

Topological sorting is used to execute dependent tasks in a valid order.

The implementation follows Kahn's algorithm:

1. Identify tasks without predecessors.
2. Execute them.
3. Remove completed dependencies.
4. Repeat until all tasks have been processed.

---

## Experimental Results

The proposed approach was evaluated through several simulation scenarios involving different workloads.

The evaluation considered:

- Allocation success rate
- Resource utilization
- Average response time
- Waiting time
- Fairness between VIP and standard clients
- Scalability under increasing workloads

> *(Insert your dashboard screenshot here)*

```text
docs/dashboard.png
```

> *(Insert your performance graphs here)*

```text
docs/performance.png
```

---

## Related Publication

**Bineta Dabo**

**Proposition d'un modèle de système multi-agents pour l'allocation équitable des ressources dans le Cloud Computing**

Accepted at **COC'2026**

HAL publication:

https://hal.science/hal-05571848

---

## Citation

If you use this repository in your research, please cite it using the information provided in the `CITATION.cff` file.

BibTeX:

```bibtex
@software{dabo2026cloudmas,
  author = {Bineta Dabo},
  title = {Cloud Resource Allocation Multi-Agent System},
  year = {2026},
  url = {https://github.com/Queen746/cloud-resource-allocation-multi-agent-system},
  orcid = {https://orcid.org/0009-0006-6853-2742}
}
```

---

## Author

**Bineta Dabo**

Master's Student in Computer Science

Cheikh Anta Diop University (UCAD), Senegal

- ORCID: https://orcid.org/0009-0006-6853-2742
- Google Scholar: https://scholar.google.com/citations?user=AxGs9B4AAAAJ&hl=fr
- LinkedIn: https://www.linkedin.com/in/bineta-dabo-4584a71b1

---

## License

This project is distributed under the MIT License.

See the **LICENSE** file for more information.

---

## Acknowledgements

The author would like to thank:

- Cheikh Anta Diop University (UCAD)
- The SPADE development community
- The organizers of COC'2026