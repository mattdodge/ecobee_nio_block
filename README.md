# Ecobee Thermostat Block

Very much a work in progress still....

## Steps to set up
1. Create a custom Ecobee app with PIN Authorization. [Docs here](https://www.ecobee.com/home/developer/api/documentation/v1/auth/pin-api-authorization.shtml)
2. Get the PIN code by performing the "Authorize Request" manually
3. Enter the PIN in your Ecobee app dashboard
4. Perform the first token request using the code from the first PIN request
5. Record the initial "refresh token" and put that in the block config
6. Put the app ID you created in step 1 for the block's app key

## Features
 - Read your thermostat's temperature and modes
 - Set your thermostat's desired temp (only until next interval)
 - Automatic retry - fetches a new access token if a request fails
 - Persists refresh tokens so you won't have to

## Still To Do
 - Individual thermostat IDs
 - Perform the initial refresh token request automatically
 - Configurable temperature setting modes (e.g., indefinitely)
 - Tests and proper block/doc structure
