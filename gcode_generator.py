import math
import os
import matplotlib.pyplot as plt

#-----CONFIGURABLE PARAMS-----
filename = "test.nc"
blade_width_in = 2.99213
wax_width_in = 2
wax_length_in = 4
z_retract_height_in = 0.04
cut_depth_in = 0.00393701  # 100um
cut_spacing_in = 0.0023622  # 60um
cut_angle_deg = 56
cut_speed_ipm = 1.0
#-----------------------------

move_log = []  # List of tuples: (x0, z0, x1, z1, type)


def write(lines):
    with open(filename, 'a') as f:
        for line in lines:
            f.write(line + '\n')


def write_header():
    gcode_lines = [
        "G00",
        "G90 G94 G17",
        "G20",
        "G28 G91 Z0.",
        "G90",
        "M09",
        "G00 G54"
    ]
    write(gcode_lines)


def rapid_move(x, y, z):
    """
    Performs a rapid positioning move to the given (X, Y) and applies Z height offset.

    Parameters:
        x, y, z: Target coordinates for the rapid move.
    """
    gcode_lines = [
        f"G00 X{x:.4f} Y{y:.4f}",
        f"G43 Z{z:.4f} H01"
    ]
    write(gcode_lines)

    # Log rapid move in XZ
    move_log.append((None, None, x, z, 'rapid'))


def angular_move(angle_deg: float, current_x: float, current_z: float, z_depth: float, down: bool = False):
    """
    Move along a diagonal in the XZ plane at a specified angle and Z depth.

    Parameters:
        angle_deg: Angle from horizontal (in degrees).
        current_x, current_z: Starting X and Z positions.
        z_depth: Total Z distance to move.
        down: If True, moves down into material; otherwise retracts.

    Returns:
        (new_x, new_z): The target coordinates after the move.
    """
    angle_rad = math.radians(angle_deg)
    dz = abs(z_depth)
    dx = dz / math.tan(angle_rad)

    if not down:
        dx = -dx
        z_depth = -z_depth

    target_x = current_x + dx
    target_z = current_z - z_depth

    gcode_lines = [
        f"G01 X{target_x:.4f} Z{target_z:.4f} F{cut_speed_ipm}."
    ]
    write(gcode_lines)

    move_type = 'cut' if down else 'retract'
    move_log.append((current_x, current_z, target_x, target_z, move_type))

    return target_x, target_z


def plot_moves():
    fig, ax = plt.subplots()
    #plot only first 50 moves
    for move in move_log[:50]:
        x0, z0, x1, z1, move_type = move

        # For rapid moves, we don't know where it came from; skip unless we know start
        if x0 is None or z0 is None:
            continue

        if move_type == 'rapid':
            ax.plot([x0, x1], [z0, z1], linestyle='--', color='blue', label='Rapid Move')
        elif move_type == 'cut':
            ax.plot([x0, x1], [z0, z1], color='red', label='Cut Down')
        elif move_type == 'retract':
            ax.plot([x0, x1], [z0, z1], color='green', label='Retract Up')

    ax.set_xlabel('X (inches)')
    ax.set_ylabel('Z (inches)')
    ax.set_title('XZ Toolpath')
    ax.grid(True)

    # Add unique legend
    handles, labels = plt.gca().get_legend_handles_labels()
    by_label = dict(zip(labels, handles))
    plt.legend(by_label.values(), by_label.keys())

    plt.show()


def main():
    if os.path.exists(filename):
        os.remove(filename)
    write_header()

    y_position = -(blade_width_in / 2) - (wax_width_in / 2)

    last_x, last_z = 0, z_retract_height_in
    rapid_move(last_x, y_position, last_z)

    for i in range(int(wax_length_in / cut_spacing_in)):
        retracted_x = i * cut_spacing_in

        # Log rapid move (assume last_x, last_z known)
        move_log.append((last_x, last_z, retracted_x, z_retract_height_in, 'rapid'))
        rapid_move(retracted_x, y_position, z_retract_height_in)

        # Move down
        inserted_x_pos, inserted_z_pos = angular_move(
            cut_angle_deg,
            retracted_x,
            z_retract_height_in,
            cut_depth_in + z_retract_height_in,
            down=True
        )

        # Move up
        last_x, last_z = angular_move(
            cut_angle_deg,
            inserted_x_pos,
            inserted_z_pos,
            cut_depth_in + z_retract_height_in,
            down=False
        )

    plot_moves()


if __name__ == "__main__":
    main()
