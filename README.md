# Energy Monitoring Stallaini

This repository contains the code and documentation for the `Energy Monitoring Stallaini` project.

The first-goal is to provide a system to monitor, remotely-control, and automate the energy system in Stallaini.

A long-term goal would be to have a system that can be generalized and used in other contexts.

## Table of Contents
- [Energy Monitoring Stallaini](#energy-monitoring-stallaini)
  - [Table of Contents](#table-of-contents)
  - [Stallaini Energy System](#stallaini-energy-system)
    - [Main loads](#main-loads)
  - [IT Architecture](#it-architecture)
  - [Configuration and Usage](#configuration-and-usage)
  - [ToDo](#todo)

## Stallaini Energy System
The energy system in Stallaini is based on a Studer system with a Pylontech battery. It is composed of the following components:
- Studer XTM 4000-48 Inverter
- Studer VarioTrack 65A MPPT
- 2x Pylontech US5000 batteries
- Studer RCC-02 Remote Control
- Studer Xcom-CAN interface

### Main loads
 - Main water pump - extracting water from the well. 2,2kW meaning around 50A at 48V
 - Water heater - 1,5kW
 - Kitchen and oven - up to 2kW
 - Other appliances - secondary water pump (from the tank to the house), fridge, lights, irrigation pump, etc.

## IT Architecture
A Raspberry Pi 4 is connected to the Studer system and the battery through a CAN bus. 

The Raspberry Pi 4 is connected to the internet using a 4G modem with limited connection traffic (200MB/month). Therefore, the system is designed to minimize the data usage for the local Pi.

To be able to access remotely the Raspberry Pi even behind a mobile network (using [CGNAT](https://en.wikipedia.org/wiki/Carrier-grade_NAT)), the Pi is connected to a VPN server. A Wireguard VPN is used.

Both the VPN server and the Telegram Bot are hosted on another Raspberry Pi, that is connected to the internet without traffic limitation, and is provided with a public IP. In the future, the server might be migrated to a cloud service.

The local Raspberry Pi runs a Python script that reads data from the CAN bus and sends it to the server through a simple API developed in python with very optimized data usage. The data is sent once every minute, which provides a good tradeoff between granularity for monitoring and data usage.

The following data is sent:
 - Battery voltage
 - Battery state of charge
 - Battery state of health
 - Battery current (provides general information about energy produced - energy consumed)
 - Battery temperature
 - Charge voltage - voltage at which the battery can be charged
 - Charge and discharge current limits

The server stores the data in a SQLite3 database. The data is then used to provide a Telegram bot that can be used to monitor the system. The bot is protected with a password that is set in the configuration file.

## Configuration and Usage
To use the system you need the following components:
- Computer Connected to the CAN bus together with the Studer system and the battery. In this case I used a Raspberry Pi 4 with a MCP2515 as a CAN to SPI converter.
- A server to host the API and the Telegram bot. Without the internet connection limitation this can be hosted on the same machine connected to the energy system. My instance is currently hosted on another Raspberry Pi.
  
The steps to configure the system are the following:
 - Create the Telegram Bot - use the BotFather to generate API keys for a bot. Save the API key in the `server/config.py` file together with the password that will be used to authenticate users to the bot.
 - Configure services using provided files:
    - `server/service_files/stallaini-server.service` - systemd service to run the API server.
    - `server/service_files/telegram-bot.service` - systemd service to run the Telegram bot.
    - `local-client/service_files/stallaini_client.service` - systemd service to run the Python client.

## ToDo
- [ ] Remove hardcoded data in the repo and create an installation script (move service files to the right place and enable them).
- [ ] Save data locally when connection is not available.
- [ ] Migrate the server to a cloud service.
- [ ] Save authenticated users in the database.
- [ ] Send notifications for logged users for events (battery alarm, battery low, heavy load on for too much time, etc.).
- [ ] Add a clearer schema to the docs, section Stallaini Energy System.
- [ ] Start working on automation features (automatic management of well pump and water heater).
- [ ] Improve granularity of consumption management (add measurements for main loads).
- [ ] Get data from the Studer system (data about inverter status, MPPT status, etc.).
- [ ] Add weather data to the system (e.g. solar irradiation).

