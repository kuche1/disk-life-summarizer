#! /usr/bin/env python3

import subprocess
import argparse

OUTPUT_SMARTCTL_ERROR = 'ERROR_SMARTCTL'

DISK_DIMENTIA_HOURS = 24 * 365.25 * 4
# assuming that a disk is going to corrupt sectors after being powered on for N hours

DISK_DEATH_HOURS = 24 * 365.25 * 14
# assuming that a disk is going to die after being powered on for N hours

def term(cmds:list[str]) -> str:
    return subprocess.run(cmds, check=True, capture_output=True).stdout.decode()

def main(disks:list[str]):
    outputs = []

    for disk in disks:
        try:
            output = term(['sudo', 'smartctl', '--all', disk])
        except subprocess.CalledProcessError:
            output = OUTPUT_SMARTCTL_ERROR

        outputs.append((disk, output))

    # disk, age_hours
    ages = []

    for disk, output in outputs:

        if output == OUTPUT_SMARTCTL_ERROR:
            ages.append((disk, output))
            continue

        key = 'Power_On_Hours'
        if key in output:
            idx = output.index(key)
            output = output[idx:]

            idx = output.find('\n')
            if idx >= 0:
                output = output[:idx]

            # print(f'{output=}')

            age = output.split('  ')[-1] # really hacky
            if age.startswith(' '):
                age = age[1:]

            # print(f'{age=}')

            idx = age.find('h+')
            if idx >= 0:
                age = age[:idx]
                # print(f'{age=}')

            idx = age.find(' (') # for example `24462 (64 151 0)` I hope that the first one is the time in hours
            if idx >= 0:
                age = age[:idx]
                # print(f'{age=}')

            age = int(age)

            # print(f'{age=}')

            ages.append((disk, age))

            continue

        key = '\nAccumulated power on time, hours:minutes '
        if key in output:
            idx = output.index(key)
            output = output[idx+len(key):]

            idx = output.find('\n')
            if idx >= 0:
                output = output[:idx]

            # print(f'{output=}')

            assert output.count(':') == 1
            age = output.split(':')[0]

            # print(f'{age=}')

            age = int(age)

            # print(f'{age=}')

            ages.append((disk, age))
            continue

        assert False

    for disk, age_hours in ages:

        if type(age_hours) == str:

            data = age_hours

        else:

            death_percent = 100 * age_hours / DISK_DEATH_HOURS

            dimentia_percent = 100 * age_hours / DISK_DIMENTIA_HOURS

            age_days = age_hours // 24
            age_hours = age_hours % 24

            age_years = age_days // 365.25
            age_days = age_days % 365.25

            data = f'dimentia[{dimentia_percent:>6.2f}%]; death[{death_percent:>6.2f}%]; years[{age_years:>1.0f}], days[{age_days:>3.0f}], hours[{age_hours:>2.0f}]'

        print(f'disk[{disk:<8}]; {data}')
        # also formatting the disk name in case in the future we need to add nvmes

if __name__ == '__main__':
    parser = argparse.ArgumentParser('summarize disk life')
    parser.add_argument('disks', type=str, nargs='+', help='disks to summarize')
    args = parser.parse_args()
    main(args.disks)
