#! /usr/bin/env python3

import subprocess
import argparse
import os

OUTPUT_SMARTCTL_ERROR = 'ERROR_SMARTCTL'

DISK_DIMENTIA_HOURS = 24 * 365.25 * 4
# assuming that a disk is going to corrupt sectors after being powered on for N hours

DISK_DEATH_HOURS = 24 * 365.25 * 14
# assuming that a disk is going to die after being powered on for N hours

class Disk:
    def __init__(self, name:str, age_hours:int|str, health:float):
        self.name = name
        self.age_hours = age_hours
        self.health = health

def term(cmds:list[str]) -> str:
    return subprocess.run(cmds, check=True, capture_output=True).stdout.decode()

def parse_age(output:str):
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

        return age

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

        return age

    return float('inf')

def parse_health(output:str):
    tmp = 'Vendor Specific SMART Attributes with Thresholds:\nID# ATTRIBUTE_NAME          FLAG     VALUE WORST THRESH TYPE      UPDATED  WHEN_FAILED RAW_VALUE\n'
    idx = output.find(tmp)
    if idx >= 0:
        output = output[idx+len(tmp):]

        worst_health = float('inf')

        for line in output.splitlines():
            if len(line) == 0:
                break

            tmp = '  '
            while tmp in line:
                line = line.replace(tmp, ' ')

            line = line.strip()

            # print(f'{line=}')
            _id, _attr, _flag, current_value, worst_value, threshold, typee, _updated, _when_failed = line.split(' ')[:9] # the raw value CAN have spaces within

            if typee.lower() != 'pre-fail':
                continue

            current_value = float(current_value)
            worst_value = float(worst_value)
            threshold = float(threshold)

            if threshold == 0:
                continue

            print(f'{current_value=} {worst_value=} {threshold=}')

            health = current_value / threshold

            print(f'{health=}')

            if health < worst_health:
                worst_health = health

        return worst_health

    else:

        return float('inf')

def main(disks:list[str]):
    outputs = []

    for disk in disks:
        try:
            output = term(['sudo', 'smartctl', '--all', disk])
        except subprocess.CalledProcessError:
            output = OUTPUT_SMARTCTL_ERROR

        outputs.append((disk, output))

    disk_objs = []

    for disk, output in outputs:
        # TODO
        # if output == OUTPUT_SMARTCTL_ERROR:
        #     return OUTPUT_SMARTCTL_ERROR
        age = parse_age(output)
        health = parse_health(output)
        disk_objs.append(Disk(disk, age, health))

    # shorten names

    longest_disk_name = 0
    for disk in disk_objs:
        disk.name = os.path.realpath(disk.name)
        disk.name = os.path.basename(disk.name)

        if len(disk.name) > longest_disk_name:
            longest_disk_name = len(disk.name)

    disk_objs.sort(key=lambda d: d.age_hours)

    for disk in disk_objs:

        if type(disk.age_hours) == str:

            age_data = age_hours

        else:

            death_percent = 100 * disk.age_hours / DISK_DEATH_HOURS

            dimentia_percent = 100 * disk.age_hours / DISK_DIMENTIA_HOURS

            age_days = disk.age_hours // 24
            age_hours = disk.age_hours % 24

            age_years = age_days // 365.25
            age_days = age_days % 365.25

            age_data = f'dimentia[{dimentia_percent:>6.2f}%]; death[{death_percent:>6.2f}%]; age_ydh[{age_years:>1.0f}/{age_days:>3.0f}/{age_hours:>2.0f}]'

        health = disk.health

        print(f'disk[{disk.name:<{longest_disk_name}}]; health[{health:4.2f}]; {age_data}')
        # also formatting the disk name in case in the future we need to add nvmes

if __name__ == '__main__':
    parser = argparse.ArgumentParser('summarize disk life')
    parser.add_argument('disks', type=str, nargs='+', help='disks to summarize')
    args = parser.parse_args()
    main(args.disks)
