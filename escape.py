import json, time
start_time = time.time()

INFINITY = 0
MIN_VALUE = -10000
CHECK = 11

def get_asteroid(data, pos):
    return data["asteroids"][pos-1]

# gives the current offset of an asteroid
def cur_asteroid_position(asteroid, time):
    # remove full cycles
    cur_offset = (asteroid['offset'] + time)%asteroid['t_per_asteroid_cycle']
    return cur_offset

# Returns True if at that position and time the spaceship will explode.
def is_dead(data, pos, time):
    if pos == -1:
        return True
    elif pos == 0:
        # we are at the surface of the planet
        pass
    elif pos < len(data["asteroids"]):
        offset = cur_asteroid_position(get_asteroid(data, pos), time)
        if offset == 0:
            return True
    else:
        return False
    # now check if it is in blast radius.
    if pos > int(time/data['t_per_blast_move'])-1:
        return False
    else:
        return True

# Determines if is okay to reach the 'idx' asteriod with velocity 'vel'.
def is_allowed(data, idx, vel, check_another_level):
    if idx >= len(data['asteroids']):
        return True
    to = data['asteroids'][idx]
    if to['min_vel'] == INFINITY:
        return False
    if 'fixed' in to and to['fixed'] == True:
        if to['min_vel'] - vel == 0 or abs(to['min_vel'] - vel) == 1:
            return True
        else:
            return False
    else:
        if to['min_vel'] <= vel:
            # check one more level
            if check_another_level:
                if is_allowed(data, idx+vel-1, vel-1, False) or is_allowed(data, idx+vel, vel, False) or is_allowed(data, idx+vel+1, vel+1, False):
                    return True
                else:
                    return False
            else:
                return True
        else:
            return False

# determines if the min_vel is the only velocity possible at this asteriod.
def is_fixed(data, idx):
    min_vel = data['asteroids'][idx]['min_vel']
    for i in range(1, CHECK):
        if is_allowed(data, idx + min_vel + i, min_vel + i, True):
            return False
    return True

# initiale min_vel and fixed for each asteriod layer. Also determine if there
# exists any bands and return them. Bands are asteriods which have
# t_per_asteroid_cycle = 1, meaning we can never reach that asteriod and have to
# just pass them.
def initialize_and_find_bands(data):
    bands = []
    is_band = False
    for i, asteroid in enumerate(data['asteroids']):
        if asteroid['t_per_asteroid_cycle'] == 1:
            asteroid['min_vel'] = INFINITY
            asteroid['fixed'] = True
            if is_band:
                bands[-1][1] = i
            else:
                bands.append([i, i])
                is_band = True
        else:
            is_band = False
            asteroid['min_vel'] = MIN_VALUE
            asteroid['fixed'] = False
    return bands[::-1]

# Based on the bands determine what should be minimum required velocity of the
# asteriod layer before the band. Then backtrack to determine min velocities of
# even lower layers. Another value 'fixed' is set True if min_vel is the only
# velocity possible at that layer.
def fill_velocities(data, bands):
    for b, band in enumerate(bands):
        if band[0] == band[1]:
            # skip small bands
            continue
        size = band[1] - band[0] + 1
        # first set of layers for which we assign the value of velocity
        # 's' is always greater than 'e'
        s = band[0]-1
        e = band[0]-size
        x = 1
        for i in range(s, e-1, -1):
            if data['asteroids'][i]['min_vel'] == INFINITY:
                continue
            min_vel = size + x
            if i+min_vel >= len(data['asteroids']):
                data['asteroids'][i]['min_vel'] = min_vel
                continue
            if data['asteroids'][i+min_vel]['min_vel'] == INFINITY:
                data['asteroids'][i]['min_vel'] = INFINITY
                data['asteroids'][i]['fixed'] = True
            else:
                if is_allowed(data, i + min_vel, min_vel, True):
                    data['asteroids'][i]['min_vel'] = min_vel
                    data['asteroids'][i]['fixed'] = is_fixed(data, i)
                else:
                    data['asteroids'][i]['min_vel'] = INFINITY
            x = x + 1

        # backtrack to fill lower levels based on newly filled levels.
        while not entering_new_band(bands, b, e):
            for i in range(s, e-1, -1):
                if data['asteroids'][i]['min_vel'] ==  INFINITY:
                    continue
                vel = data['asteroids'][i]['min_vel']
                for a in [1, 0, -1]:
                    prev_vel = vel - a
                    prev_idx = i - prev_vel
                    if data['asteroids'][prev_idx]['min_vel'] ==  INFINITY:
                        continue
                    elif data['asteroids'][prev_idx]['min_vel'] == MIN_VALUE:
                        data['asteroids'][prev_idx]['min_vel'] = prev_vel
                    else:
                        data['asteroids'][prev_idx]['min_vel'] = min(prev_vel, data['asteroids'][prev_idx]['min_vel'])

            # now determine if this min_vel is fixed or not
            ns = e - 1
            ne = ns - data['asteroids'][ns]['min_vel'] + 2
            should_break = False
            if entering_new_band(bands, b, ne):
                ne = bands[b+1][1] + 1
                should_break = True
            for i in range(ns, ne-1, -1):
                if data['asteroids'][i]['min_vel'] == MIN_VALUE:
                    data['asteroids'][i]['min_vel'] = INFINITY
                    data['asteroids'][i]['fixed'] = True
                elif data['asteroids'][i]['min_vel'] == INFINITY:
                    data['asteroids'][i]['fixed'] = True
                else:
                    data['asteroids'][i]['fixed'] = is_fixed(data, i)
            e, s = ne, ns
            if should_break or e == s:
                break

# Returns True if while backtracking we are reaching another band.
def entering_new_band(bands, idx, end):
    if idx+1 < len(bands) and bands[idx+1][1] > end:
        return True
    return False

def preprocess_data(data):
    bands = initialize_and_find_bands(data)
    fill_velocities(data, bands)

# determines if the attained velocity at the layer is valid or not.
def is_valid_velocity(data, pos, vel):
    if pos < 1:
        return True
    asteroid = get_asteroid(data, pos)
    if asteroid['fixed']:
        if vel != asteroid['min_vel']:
            return False
    else:
        if vel < asteroid['min_vel']:
            return False
    return True

# determines the final escape route.
def determine_escape_route(data):
    # stack contains tuple (acceleration, velocity, position).
    stack = [(0, 0, 0)] # in the beginning we are on the surface
    p, v, t, a = 0, 0, 0, -1
    while p >= 0 and p <= len(data["asteroids"]) and len(stack) > 0:
        sol = False
        while a < 2:
            new_v = v + a
            new_p = p + new_v
            if not is_valid_velocity(data, p, new_v) or is_dead(data, new_p, t+1):
                a = a + 1
            else:
                # no collision
                stack.append((a, new_v, new_p))
                p, v, t, a = new_p, new_v, t+1, -1
                sol = True
                break
        if not sol:
            # None of the possibilities worked so remove the last state and retry.
            last_state = stack.pop()
            a = last_state[0] + 1
            _, v, p = stack[len(stack)-1]
            t = t - 1

    out = []
    if p > len(data["asteroids"]):
        print('Successfully Escaped :)')
        out = [i[0] for i in stack]
        out = out[1:]
    return out

data = json.load(open('v3_chart.json'))
INFINITY = len(data["asteroids"])
print
print('Number of asteroids to dodge: ' + str(len(data["asteroids"])))

preprocess_data(data)
route = determine_escape_route(data)
print
print('Escape route is:')
print(route)
print
print('Time taken: ' + str(len(route)) + 't')
print('Time taken to determine the route: ' + str(time.time() - start_time) + ' seconds')
