#include <linux/delay.h>
#include <linux/device.h>
#include <linux/fs.h>
#include <linux/gpio.h>
#include <linux/interrupt.h>
#include <linux/miscdevice.h>
#include <linux/module.h>
#include <linux/time.h>
#include <linux/uaccess.h>

#define DEV_NAME "rht03"
#define DEFAULT_GPIO_PIN 4
#define DATA_BYTES 5

static struct timespec prev_time;
static unsigned char data_buf[DATA_BYTES];
static int bit_count;
static int gpio_pin = DEFAULT_GPIO_PIN;
static int rht03_irq = -1;
static bool return_zero = false;

/* ISR called on every GPIO falling edge */
static irqreturn_t rht03_isr(int irq, void *data)
{
	struct timespec cur_time, delta;
	int us;

	getnstimeofday(&cur_time);
	delta = timespec_sub(cur_time, prev_time);
	us = (delta.tv_sec * 1000000) + (delta.tv_nsec / 1000);
	/*
	 * Ignore the first two edges because they are not data bits
	 * Ignore any edges after the expected number of bits are captured
	 * Zero bits are ~80 us, one bits are ~120 us
	 * Only shift in the one bits since the data buffer is already set to zero
	 */
	if (bit_count > 1 && bit_count < 42 && us > 100) {
		data_buf[((bit_count - 2) / 8)] |= 1 << (7 - ((bit_count - 2) % 8));
	}
	bit_count++;
	prev_time = cur_time;

	return IRQ_HANDLED;
}

static int rht03_open(struct inode *inode, struct file *file)
{
	return nonseekable_open(inode, file);
}

static int rht03_release(struct inode *inode, struct file *file)
{
	return 0;
}

static ssize_t rht03_write(struct file *file, const char __user *buf, size_t count, loff_t *pos)
{
	return -EINVAL;
}

static ssize_t rht03_read(struct file *file, char __user *buf, size_t count, loff_t *pos)
{
	int i, h, t, err, s_count = 0;
	unsigned char chk = 0;
	char str[32];

	/*  */
	if (return_zero) {
		return_zero = false;
		return 0;
	}

	/* Start timing falling edges */
	getnstimeofday(&prev_time);

	/* Send start signal */
	err = gpio_direction_output(gpio_pin, 0);
	if (err) {
		printk(KERN_ERR "%s: gpio_direction_output(%d, 0) returned %d\n", __func__, gpio_pin, err);
		return -EFAULT;
	}
	usleep_range(1000, 20000);
	err = gpio_direction_input(gpio_pin);
	if (err) {
		printk(KERN_ERR "%s: gpio_direction_input(%d) returned %d\n", __func__, gpio_pin, err);
		return -EFAULT;
	}

	/* Capture data */
	bit_count = 0;
	memset(data_buf, 0, sizeof data_buf);
	enable_irq(rht03_irq);
	usleep_range(5000, 10000);
	disable_irq(rht03_irq);

	/* Check validity of data */
	if (bit_count != (DATA_BYTES * 8 + 2)) {
		printk(KERN_ERR "%s: expected %d bits, but only received %d\n", __func__, DATA_BYTES * 8 + 2, bit_count);
		return -EFAULT;
	}
	for (i = 0; i < DATA_BYTES - 1; i++) {
		chk += data_buf[i];
	}
	if (chk != data_buf[DATA_BYTES - 1]) {
		printk(KERN_ERR "%s: expected checksum 0x%02x, but calculated 0x%02x\n", __func__, data_buf[DATA_BYTES - 1], chk);
		return -EFAULT;
	}

	/* Convert data to decimal values */
	h = (data_buf[0] << 8) + data_buf[1];
	t = ((data_buf[2] & 0x7f) << 8) + data_buf[3];
	if (data_buf[2] & 0x80) {
		t = 0 - t;
	}

	/* Copy values back to userland */
	sprintf(str, "h=%d t=%d\n", h, t);
	s_count = strlen(str);
	err = copy_to_user(buf, str, s_count + 1);
	if (err != 0) {
		printk(KERN_ERR "%s: copy_to_user returned %d\n", __func__, err);
		return -EFAULT;
	}

#if(0)
	/* XXX debug */
	for (i = 0; i < DATA_BYTES; i++) {
		printk(KERN_INFO "rht03 %d 0x%02x\n", i, data_buf[i]);
	}
#endif

	return_zero = true;
	return s_count;
}

static struct file_operations rht03_fops = {
	.owner = THIS_MODULE,
	.open = rht03_open,
	.read = rht03_read,
	.write = rht03_write,
	.release = rht03_release,
};

static struct miscdevice rht03_misc_device = {
	.minor = MISC_DYNAMIC_MINOR,
	.name = DEV_NAME,
	.fops = &rht03_fops,
	.mode = 0666,
};

static int __init rht03_init(void){
	int ret = 0;
	printk(KERN_INFO "%s: start\n", __func__);

	ret = gpio_request(gpio_pin, "input");
	if (ret) {
		printk(KERN_ERR "%s: gpio_request(%d, \"input\") returned %d\n", __func__, gpio_pin, ret);
		goto fail;
	}
	ret = gpio_direction_input(gpio_pin);
	if (ret) {
		printk(KERN_ERR "%s: gpio_direction_input(%d) returned %d\n", __func__, gpio_pin, ret);
		goto fail;
	}
	ret = gpio_to_irq(gpio_pin);
	if (ret < 0) {
		printk(KERN_ERR "%s: gpio_to_irq(%d) returned %d\n", __func__, gpio_pin, ret);
		goto fail;
	}
	rht03_irq = ret;
	ret = request_irq(rht03_irq, rht03_isr, IRQF_TRIGGER_FALLING, "rht03", NULL);
	if (ret) {
		printk(KERN_ERR "%s: request_irq returned %d\n", __func__, ret);
		free_irq(rht03_irq, NULL);
		goto fail;
	}
	disable_irq(rht03_irq);

	misc_register(&rht03_misc_device);

	printk(KERN_INFO "%s: gpio_pin=%d\n", __func__, gpio_pin);
	printk(KERN_INFO "%s: end\n", __func__);
	return ret;

fail:
	gpio_free(gpio_pin);
	return ret;
}

static void __exit rht03_exit(void){
	printk(KERN_INFO "%s: start\n", __func__);

	misc_deregister(&rht03_misc_device);
	free_irq(rht03_irq, NULL);
	gpio_free(gpio_pin);

	printk(KERN_INFO "%s: end\n", __func__);
}

module_init(rht03_init);
module_exit(rht03_exit);

module_param(gpio_pin, int, S_IRUGO);
MODULE_PARM_DESC(gpio_pin, "GPIO pin number wired to RHT03 sensor (default #DEFAULT_GPIO_PIN)");

MODULE_LICENSE("GPL");
MODULE_AUTHOR("Michael Johns <michaelwaynejohns@gmail.com>");
MODULE_DESCRIPTION("RHT03 device driver");
