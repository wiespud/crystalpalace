#include <errno.h>
#include <fcntl.h>
#include <limits.h>
#include <linux/i2c-dev.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/ioctl.h>
#include <unistd.h>

#define FREQ_DEV "/dev/freq"
#define I2C_DEV "/dev/i2c-1"
#define I2C_ADDR 0x51
#define READ_POS 10
#define READ_LEN 4

/*
 * The HH10D stores its calibration factors in an M24C02 EEPROM.
 *      Address Factor      Byte
 *      10      Sensitivity MSB
 *      11      Sensitivity LSB
 *      12      Offset      MSB
 *      13      Offset      LSB
 */
int get_cal_factors(int *sensitivity, int *offset)
{
	int i, i2c_fd;
	unsigned char buf[READ_LEN];

	/* Open the i2c device and set the slave address */
	if ((i2c_fd = open(I2C_DEV, O_RDWR)) < 0) {
		fprintf(stderr, "Failed to open %s, errno = %d\n", I2C_DEV, errno);
		return -1;
	}
	if (ioctl(i2c_fd, I2C_SLAVE, I2C_ADDR) < 0) {
		fprintf(stderr, "Failed to set slave address 0x%02x, errno = %d\n", I2C_ADDR, errno);
		return -1;
	}

	/* Read bytes that contain calibration factors */
	buf[0] = READ_POS;
	if (write(i2c_fd, buf, 1) != 1) {
		fprintf(stderr, "Failed to seek to byte %d in %s, errno = %d\n", READ_POS, I2C_DEV, errno);
		return -1;
	}
	if (read(i2c_fd, buf, READ_LEN) != READ_LEN) {
		fprintf(stderr, "Failed to read %d bytes from %s, errno = %d\n", READ_LEN, I2C_DEV, errno);
		return -1;
	}
	*sensitivity = buf[1] | buf[0] << 8;
	*offset = buf[3] | buf[2] << 8;

#if(1)
	for (i = 0; i < READ_LEN; i++) {
		printf("%02x ", buf[i]);
	}
	printf("\n");
#endif

	return 0;
}

/*
 * The equation to calculate the relative humidity is
 *      RH = (offset - frequency) * sensitivity / 2^12
 */
int main()
{
	int sens, offs, len, rh, rc = -1;
	long freq;
	FILE *freq_fd;
	char *freq_str, *end;

	if(get_cal_factors(&sens, &offs) < 0) {
		fprintf(stderr, "Failed to get calibration factors\n");
		goto fail;
	}
	printf("sensitivity = %d, offset = %d\n", sens, offs);

	/* Read sensor frequency */
	freq_fd = fopen(FREQ_DEV, "r");
	if (freq_fd == NULL) {
		fprintf(stderr, "Failed to open %s, errno = %d\n", FREQ_DEV, errno);
		goto fail;
	}
	if (getline(&freq_str, &len, freq_fd) < 0) {
		fprintf(stderr, "Failed to read from %s, errno = %d\n", FREQ_DEV, errno);
		goto fail;
	}
	printf("frequency string = %s", freq_str);

	/* Convert sensor reading to relative humidity */
	freq = strtol(freq_str, &end, 10);
	if (freq == 0 || freq == LONG_MIN || freq == LONG_MAX || end == freq_str) {
		fprintf(stderr, "Failed to convert %s, errno = %d\n", freq_str, errno);
		goto fail;
	}
	printf("frequency = %ld\n", freq);
	rh = ((offs - freq) * sens) >> 12;
	printf("relative humidity = %d\n", rh);

fail:
	if (freq_str) {
		free(freq_str);
	}
	return 0;
}