AN: PA3569BUXRYA
KEY: PK5IS7UDIKUUR6PZXC7JJG6H6D
SECRET: Fc81zZdSbiqezthSnN2oRHjyc4paqQbH5WPg3qEWbYrC


Deployment running but there's a config issue on VPS. The live account 935928263 has SectorRotationAdaptive_v1 but should be SectorRotationAdaptive_v3. Also the new account PA3569BUXRYA is missing.

The sed command may have been applied but the old config was already loaded. Let me check the current VPS config and restart again:

Found the problem! The docker-compose.yml mounts to the **old** path /app/production/configs/accounts.yaml but the code now reads from

  /app/configs/accounts.yaml. Need to update the VPS docker-compose: