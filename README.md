# Detecting and alerting traders when campaign objects prematurely hit budget caps

This script takes CSV (from DBM and Appnexus) files containing the budget settings of campaign objects and how much money they spent the day before.
The objects that spent all of their allocated budgets are flagged, and matched to the relevant person trading the campaign. 
A list of campaign objects that hit their budgets is created for each trader and emailed to them every morning.
