from machine import I2C, Pin
import time


class PCA9685:
    MODE1 = 0x00
    MODE2 = 0x01
    PRESCALE = 0xFE
    LED0_ON_L = 0x06

    def __init__(self, i2c, address=0x40, pwm_freq=1000):
        self.i2c = i2c
        self.address = address
        self.reset()
        self.set_pwm_freq(pwm_freq)

    def _write8(self, register, value):
        self.i2c.writeto_mem(self.address, register, bytes((value & 0xFF,)))

    def _read8(self, register):
        return self.i2c.readfrom_mem(self.address, register, 1)[0]

    def reset(self):
        self._write8(self.MODE1, 0x00)
        self._write8(self.MODE2, 0x04)
        time.sleep_ms(10)

    def set_pwm_freq(self, freq_hz):
        freq_hz = max(1, min(1600, int(freq_hz)))
        prescale = int(25000000 / (4096 * freq_hz) - 1 + 0.5)

        old_mode = self._read8(self.MODE1)
        sleep_mode = (old_mode & 0x7F) | 0x10
        self._write8(self.MODE1, sleep_mode)
        self._write8(self.PRESCALE, prescale)
        self._write8(self.MODE1, old_mode)
        time.sleep_ms(5)
        self._write8(self.MODE1, old_mode | 0xA1)

    def set_pwm(self, channel, on, off):
        if not 0 <= channel <= 15:
            raise ValueError('channel must be 0..15')

        register = self.LED0_ON_L + 4 * channel
        data = bytes((on & 0xFF, (on >> 8) & 0x0F, off & 0xFF, (off >> 8) & 0x0F))
        self.i2c.writeto_mem(self.address, register, data)

    def set_duty(self, channel, duty):
        duty = max(0, min(4095, int(duty)))
        self.set_pwm(channel, 0, duty)

    def off(self, channel):
        self.set_pwm(channel, 0, 0)

    def full_on(self, channel):
        self.set_pwm(channel, 4096, 0)


class MotorDriver:
    MOTOR_COUNT = 64
    MOTORS_PER_BOARD = 8
    CHANNELS_PER_MOTOR = 2

    def __init__(self, i2c, addresses, pwm_freq=1000):
        if len(addresses) != 8:
            raise ValueError('exactly 8 PCA9685 addresses are required')

        self.i2c = i2c
        self.addresses = addresses
        self.pwm_freq = pwm_freq
        self.available = self.i2c.scan()
        self.boards = []

        for address in addresses:
            if address not in self.available:
                raise OSError('PCA9685 not found at address 0x{:02X}'.format(address))
            self.boards.append(PCA9685(i2c, address, pwm_freq))

        self.stop_all()

    def _motor_map(self, motor_id):
        if not 0 <= motor_id < self.MOTOR_COUNT:
            raise ValueError('motor_id must be 0..63')

        board_index = motor_id // self.MOTORS_PER_BOARD
        local_motor = motor_id % self.MOTORS_PER_BOARD
        base_channel = local_motor * self.CHANNELS_PER_MOTOR
        return self.boards[board_index], board_index, base_channel, base_channel + 1

    def speed_to_pwm(self, speed):
        speed = max(0, min(100, abs(int(speed))))
        return speed * 4095 // 100

    def set_motor(self, motor_id, speed):
        board, board_index, in1, in2 = self._motor_map(motor_id)
        speed = max(-100, min(100, int(speed)))
        duty = self.speed_to_pwm(speed)

        if speed > 0:
            board.set_duty(in1, duty)
            board.set_duty(in2, 0)
        elif speed < 0:
            board.set_duty(in1, 0)
            board.set_duty(in2, duty)
        else:
            board.set_duty(in1, 0)
            board.set_duty(in2, 0)

        return {
            'motor_id': motor_id,
            'board_index': board_index,
            'board_address': self.addresses[board_index],
            'in1': in1,
            'in2': in2,
            'speed': speed,
            'duty': duty,
        }

    def stop_motor(self, motor_id):
        self.set_motor(motor_id, 0)

    def stop_all(self):
        for motor_id in range(self.MOTOR_COUNT):
            self.set_motor(motor_id, 0)

    def run_all(self, speed):
        for motor_id in range(self.MOTOR_COUNT):
            self.set_motor(motor_id, speed)

    def set_motor_group(self, motor_ids, speed):
        for motor_id in motor_ids:
            self.set_motor(motor_id, speed)

    def apply_profile(self, profile, hold_ms=120):
        for motor_id, speed in profile:
            self.set_motor(motor_id, speed)
            time.sleep_ms(hold_ms)

    def test_cycle(self, run_ms=300, pause_ms=120, speed=60):
        for motor_id in range(self.MOTOR_COUNT):
            print('Motor {:02d} forward'.format(motor_id))
            self.set_motor(motor_id, speed)
            time.sleep_ms(run_ms)

            print('Motor {:02d} stop'.format(motor_id))
            self.stop_motor(motor_id)
            time.sleep_ms(pause_ms)

            print('Motor {:02d} reverse'.format(motor_id))
            self.set_motor(motor_id, -speed)
            time.sleep_ms(run_ms)

            print('Motor {:02d} stop'.format(motor_id))
            self.stop_motor(motor_id)
            time.sleep_ms(pause_ms)

    def motion_from_web_params(self, wind_speed=38, wave_amplitude=44, turbulence=26,
                               wave_complexity=54, pollution_density=31):
        flow_speed = self._map_range(wind_speed, 0, 100, 0.22, 2.15)
        displacement_range = self._map_range(wave_amplitude, 0, 100, 12, 62)
        turbulence_strength = self._map_range(turbulence, 0, 100, 0.08, 8.5)
        phase_spread = self._map_range(wave_complexity, 0, 100, 0.08, 0.42)
        density_sink = self._map_range(pollution_density, 0, 100, 0, 30)

        return {
            'wind_speed': wind_speed,
            'wave_amplitude': wave_amplitude,
            'turbulence': turbulence,
            'wave_complexity': wave_complexity,
            'pollution_density': pollution_density,
            'flow_speed': flow_speed,
            'displacement_range': displacement_range,
            'turbulence_strength': turbulence_strength,
            'phase_spread': phase_spread,
            'density_sink': density_sink,
        }

    def run_wave_frame(self, t, params=None):
        if params is None:
            params = self.motion_from_web_params()

        flow_speed = params['flow_speed']
        displacement_range = params['displacement_range']
        turbulence_strength = params['turbulence_strength']
        phase_spread = params['phase_spread']
        density_sink = params['density_sink']

        for row in range(8):
            for col in range(8):
                motor_id = row * 8 + col
                radial = self._radial_wave(row, col, t, flow_speed)
                directional = self._directional_wave(row, col, t, flow_speed)
                cross = self._cross_wave(row, col, t, flow_speed)
                wave = radial * 0.58 + directional * 0.30 + cross * 0.12
                secondary = self._sin((row + col) * 0.34 + t * flow_speed * (0.92 + phase_spread))
                motion = wave + secondary * 0.18
                density = self._density_weight(row, col)
                target = motion * displacement_range * (1.0 - density * 0.25) - density * density_sink
                target += self._noise(row, col, t) * turbulence_strength * 0.08
                speed = int(max(-100, min(100, target)))
                self.set_motor(motor_id, speed)

    def run_wave_demo(self, duration_s=10, frame_ms=80, **web_params):
        start = time.ticks_ms()
        frame = 0
        params = self.motion_from_web_params(**web_params)

        while time.ticks_diff(time.ticks_ms(), start) < duration_s * 1000:
            t = frame * frame_ms / 1000.0
            self.run_wave_frame(t, params)
            time.sleep_ms(frame_ms)
            frame += 1

        self.stop_all()

    def _map_range(self, value, in_min, in_max, out_min, out_max):
        if in_max == in_min:
            return out_min
        ratio = (value - in_min) / (in_max - in_min)
        return out_min + ratio * (out_max - out_min)

    def _sin(self, x):
        import math
        return math.sin(x)

    def _cos(self, x):
        import math
        return math.cos(x)

    def _sqrt(self, x):
        import math
        return math.sqrt(x)

    def _atan2(self, y, x):
        import math
        return math.atan2(y, x)

    def _radial_wave(self, row, col, t, speed):
        center = 3.5
        dx = col - center
        dy = row - center
        distance = self._sqrt(dx * dx + dy * dy)
        return self._sin(distance * 1.18 - t * speed * 2.2)

    def _directional_wave(self, row, col, t, speed):
        return self._sin((row + col) * 0.58 - t * speed * 1.7)

    def _cross_wave(self, row, col, t, speed):
        return self._cos((col - row) * 0.72 - t * speed * 1.28)

    def _density_weight(self, row, col):
        center = 3.5
        dx = row - center
        dy = col - center
        distance = self._sqrt(dx * dx + dy * dy)
        return max(0.0, 1.0 - distance / 5.0)

    def _noise(self, row, col, t):
        return self._sin(row * 12.9898 + col * 78.233 + t * 3.117) * 0.5


def init_i2c(scl_pin=22, sda_pin=21, freq=400000, bus_id=0):
    return I2C(bus_id, scl=Pin(scl_pin), sda=Pin(sda_pin), freq=freq)


def main():
    addresses = [0x40, 0x41, 0x42, 0x43, 0x44, 0x45, 0x46, 0x47]

    i2c = init_i2c()
    found = i2c.scan()
    print('I2C scan result:', [hex(addr) for addr in found])

    driver = MotorDriver(i2c, addresses, pwm_freq=1000)

    print('64-motor system ready')
    print('Running sequential test cycle...')
    driver.test_cycle(run_ms=200, pause_ms=80, speed=65)

    print('Running web-parameter wave demo...')
    driver.run_wave_demo(
        duration_s=8,
        frame_ms=100,
        wind_speed=38,
        wave_amplitude=44,
        turbulence=26,
        wave_complexity=54,
        pollution_density=31,
    )

    print('All tests completed')
    driver.stop_all()


if __name__ == '__main__':
    main()
