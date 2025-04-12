# Wheel Tracker - Home Assistant Add-on

This repository contains a Home Assistant add-on for tracking options trading with the "Wheel Strategy."

## About the Wheel Strategy

The Wheel Strategy is a popular options trading approach that consists of:

1. Selling Cash Secured Puts (CSPs) on stocks you'd be willing to own
2. If assigned, holding the shares
3. Selling Covered Calls (CCs) on those shares to generate additional income
4. If the shares are called away, returning to step 1

This add-on provides a clean interface to track all parts of this strategy.

## Installation

To add this repository to your Home Assistant instance:

1. Go to Settings → Add-ons → Add-on Store
2. Click the menu in the top right (three dots)
3. Select "Repositories"
4. Add this repository URL: `https://github.com/osufan129/wheel-tracker-addon`
5. Click "Add"

After adding the repository:

1. Find the "Wheel Tracker" add-on in the store
2. Click "Install"
3. Start the add-on
4. Access it from the sidebar

## Configuration

The add-on has the following configuration options:

- **database_path**: Path to store the SQLite database (default: `/config/wheel-tracker/database.db`)
- **log_level**: Controls the verbosity of log output from the add-on

## Features

- Track Cash Secured Puts (CSPs)
- Manage Share Holdings
- Track Covered Calls (CCs)
- Plan CSP trades with built-in calculator
- View trading history and performance

## Support

If you encounter any issues with this add-on, please open an issue on GitHub. 