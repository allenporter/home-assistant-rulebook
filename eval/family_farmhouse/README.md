# home1

This evaluation uses the framework in `home_assistant_datasets` to perform
an evaluation using a synthetic home and an actual LLM.

The evaluation is driven using pytest and the Home Assistant test harness, plus
the `synthetic_home` custom component.

## Running evaluation

You can run the evaluation with
```
$ pytest -m eval
```

## Home

The synthetic home is https://github.com/allenporter/home-assistant-datasets/blob/main/datasets/devices-v3/family-farmhouse-us.yaml

You can re-create the eval fixture inventory from the homoe config with the
follow command:

```bash
$ synthetic-home create_inventory eval/home1/_home.yaml > eval/home1/_fixtures.yaml
```

## Rulebook

See `rulebook.md` for the current rulebook under evaluation.

## Potential future rules

- Light in the Kitchen should turn on automatically when motion is detected during evening hours and turn off after 5 minutes of no activity.
- The Family Room Light should dim to 50% brightness when the Smart Speaker is playing music.
- Master Bedroom Light should turn off automatically at 10 PM if no one is in the room.
- Backyard Light should activate when motion is detected in the backyard after dark.
- The Smart Sprinkler System in the Backyard should run daily at 6 AM, adjusting schedule based on local weather forecasts.
- Barn Light should turn on when the Motion Sensor in the Barn detects activity and turn off after 10 minutes of no activity.
- Security Camera in the Front Yard should record and send alerts when motion is detected.
- Laundry Room Light should turn on when the door opens and turn off when the laundry cycle finishes.
- The Thermostat in the Family Room should maintain a temperature of 72°F during the day and 68°F at night.
- Notify me urgently if any smoke or CO detectors (not yet installed) detect an emergency.
- Notify me when any smart device goes offline or reports a critically low battery.
- Ensure all smart plugs (Kitchen, Laundry Room) automatically turn off connected devices if they are idle for more than 30 minutes.
