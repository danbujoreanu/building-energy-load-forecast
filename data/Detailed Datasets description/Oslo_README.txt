README: Hourly Sub-Metered Energy Use Data from 48 Public School Buildings in Oslo

Dataset Overview
This dataset contains hourly sub-metered energy use data from 48 public school buildings in Oslo, Norway, managed by Oslobygg KF. 
The dataset includes one CSV-file per building in the dataset containing meta data about the building and hourly time series data of energy use and weather data from the buildings.
The energy use data varies between buildings, but consists of main meters (electricity and district heating), sub-meters (eg. heat pumps, electric vehicle charging, cooling etc.) and energy generation (PV).

Dataset accessability
Repository name: data.sintef.no
Data identification number: 10.60609/2hvr-wc82
Direct URL to repository: https://data.sintef.no/product/dp-679b0640-834e-46bd-bc8f-8484ca79b414
Instructions  for accessing the data: The repository is open access and does not require sign-in registration.

Data Summary
- Number of buildings: 48
- Time series resolution: Hourly
- Time series duration: 1 to 11 years per building

Data sources:
- Restructured, relabled and treated energy data from Oslobygg KF’s energy surveillance system, Energinet.
- Weather data from MET Nordic Database Norway.
- Meta data from various sources.

Files and Structure
Each CSV file consists of:
1. Metadata Section
- General building details including ID, construction year, floor area, number of users (students).
- Heating and cooling system details
- EV charging information
- PV generation information
2. Time Series Data Section
- Timestamp format: %Y-%m-%dT%H:%M:%S%z (local normal time: CET, UTC+01:00)
- Weather columns: outdoor temperature, wind speed, wind direction, relative humidity and solar radiation
- Energy columns: Main or sub-meters [Wh/h]


Codes Used in CSV Files
Metadata Categories
- Header_line: First line of measurements in the CSV file
- Location: Post code or location of the building
- Year_of_construction: Year the building was constructed
- Floor_area: Floor area in square meters
- Number_of_users: Number of users in the building
- Number_of_buildings: Number of buildings on the lot
- Building_category: Building type (e.g., Sch for School)
- Energy_label: Energy efficiency label (A-G)
- Notes: Additional information about the building and energy data
- Central_heating_system: Indicates if the building has a central heating system
- Dhw_heat_source: Type of heating technology for domestic hot water
- Sh_heat_source: Type of heating technology for space heating
- Ventilation_heat_source: Type of heating technology for ventilation heating
- Pv: Photovoltaic system specifications
- Timestamp_format: Format for timestamps in the time series
- Time_zone: Time zone of the dataset (UTC+01:00)
- Building_id: Unique identifier for the building

Metadata Codes:
- Sch: School building category
- A-G: Energy label categories
- 0: No
- 1: Yes
- 2: Unknown
- EB: Electric boiler
- EFH: Electric floor heater
- EH: Electric heater
- DH: District heating
- GSHP: Ground source heat pump
- ASHP: Air source heat pump
- SC: Solar collector
- HWH: Hot water heater
- EHB: Electric heating battery

Weather Columns:
- Tout: Outdoor temperature (Celsius)
- SolGlob: Global Solar Horizontal Radiation (W/m2)
- WindSpd: Wind speed (m/s)
- WindDir: Wind direction (degrees)
- RH: Relative humidity (%)

Energy Columns:
- ElImp: Imported electricity (Wh/h)
- ElPV: Electricity production from photovoltaic panels (Wh/h)
- ElLight: Electricity used for lighting (Wh/h)
- ElBoil: Electricity used for electric boilers (Wh/h)
- ElHP: Electricity used for heat pumps (Wh/h)
- ElEV: Electricity used for electric vehicle charging (Wh/h)
- ElTech: Electricity for technical rooms (Wh/h)
- ElPump: Electricity used for pumps (Wh/h)
- ElSnow: Electricity used for snow melting systems (Wh/h)
- HtTot: Total heating energy use (Wh/h)
- HtSpace: Space heating (Wh/h)
- HtDHW: Domestic hot water heating (Wh/h)
- HtVent: Ventilation heating (Wh/h)
- HtHP: Heat from heat pumps (Wh/h)
- HtDH: Heat from district heating (Wh/h)
- HtSC: Heat from solar collectors (Wh/h)
- HtSnow: Heat used for snow melting systems (Wh/h)

Applications
The dataset can be used for:
- Energy benchmarking and validation of building simulations
- Heating disaggregation research
- Energy time series classification and forecasting
- Grid planning and energy flexibility studies

Limitations
- Sub-meter quality varies, and users should assess data before resampling
- Gaps exist in some time series, though AMS meters and district heating meters are more reliable
- The dataset is specific to Oslo schools, which are within the same climate zone and under the same municipal management

Citation
If you use this dataset, please cite:
Synne Krekling Lien, Bjørn Ludvigsen, Harald Taxt Walnum, Aileen Yang, Åse Lekang Sørensen & Kamilla Heimar Andersen. Hourly Sub-Metered Energy Use Data from 48 Public School Buildings in Oslo, Norway. Data in Brief [Submitted to, 01.04.2025]

Contact
For questions about the dataset, contact:
Synne Krekling Lien (SINTEF Community)
Email: synne.lien@sintef.no

Acknowledgements
This data is published with permission from Oslobygg KF, and we greatly appreciate their willingness to share access to it. The dataset is provided by the projects Coincidence Factors and Peak Loads of Buildings in the Norwegian Low Carbon Society (COFACTOR), funded by the Research Council of Norway and partners under grant number 326891, and Smart Building Hub (SBHub), funded by the Research Council of Norway's INFRA program under grant agreement No. 322573.

License
This dataset is licensed under Creative Commons Attribution 4.0 (CC BY 4.0).