#include <linux/device.h>
#include <linux/fs.h>
#include <linux/gpio.h>
#include <linux/interrupt.h>
#include <linux/miscdevice.h>
#include <linux/module.h>
#include <linux/time.h>
#include <linux/uaccess.h>

#define DEV_NAME "freq"
#define DEFAULT_GPIO_PIN 17
#define DEFAULT_MIN_FREQ 5000
#define DEFAULT_MAX_FREQ 10000
#define BUFFER_SIZE 256

static struct timespec prev_time;
static unsigned long ns_periods[BUFFER_SIZE];
static int buf_ptr;
static int gpio_pin = DEFAULT_GPIO_PIN;
static int min_freq = DEFAULT_MIN_FREQ;
static int max_freq = DEFAULT_MAX_FREQ;
static int freq_irq = -1;

/* ISR called on every GPIO signal edge */
static irqreturn_t freq_isr(int irq, void *data)
{
	struct timespec cur_time;
	struct timespec delta;
	unsigned long ns;

	getnstimeofday(&cur_time);
	delta = timespec_sub(cur_time, prev_time);
	ns = ((long long)delta.tv_sec * 1000000000) + delta.tv_nsec;
	ns_periods[buf_ptr] = ns;
	prev_time = cur_time;
	buf_ptr = (buf_ptr + 1) % BUFFER_SIZE;

	return IRQ_HANDLED;
}

static int freq_open(struct inode *inode, struct file *file)
{
	return nonseekable_open(inode, file);
}

static int freq_release(struct inode *inode, struct file *file)
{
	return 0;
}

static ssize_t freq_write(struct file *file, const char __user *buf, size_t count, loff_t *pos)
{
	return -EINVAL;
}

static ssize_t freq_read(struct file *file, char __user *buf, size_t count, loff_t *pos)
{
	int i, err, hz, s_count = 0;
	unsigned long sample, sum = 0;
	char str[16];

	/* Sum the samples without interference from the ISR */
	disable_irq(freq_irq);
	for (i = 0; i < BUFFER_SIZE; i += 2) {
		sample = ns_periods[i] + ns_periods[i + 1];
		hz = 1000000000 / sample;
		if (hz >= min_freq && hz <= max_freq) {
			sum += sample;
			s_count++;
		}
	}
	memset(ns_periods, 0, sizeof ns_periods);
	buf_ptr = 0;
	enable_irq(freq_irq);

	/* Average the samples if the majority are valid */
	if (s_count > BUFFER_SIZE / 4) {
		sample = sum / s_count;
		if (sample > 0) {
			hz = 1000000000 / sample;
		} else {
			return 0;
		}
	} else {
		return 0;
	}

	/* Copy the average back to userland */
	sprintf(str, "%d\n", hz);
	s_count = strlen(str);
	err = copy_to_user(buf, str, s_count + 1);
	if (err != 0) {
		printk(KERN_ERR "%s: copy_to_user returned %d\n", __func__, err);
		return -EFAULT;
	}

	return s_count;
}

static struct file_operations freq_fops = {
	.owner = THIS_MODULE,
	.open = freq_open,
	.read = freq_read,
	.write = freq_write,
	.release = freq_release,
};

static struct miscdevice freq_misc_device = {
	.minor = MISC_DYNAMIC_MINOR,
	.name = DEV_NAME,
	.fops = &freq_fops,
};

static int __init freq_init(void){
	int ret = 0;
	printk(KERN_INFO "%s: start\n", __func__);

	getnstimeofday(&prev_time);
	memset(ns_periods, 0, sizeof ns_periods);
	buf_ptr = 0;

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
	freq_irq = ret;
	/* Interrupt on rising and falling edges to better handle glitchy signals */
	ret = request_irq(freq_irq, freq_isr, IRQF_TRIGGER_RISING | IRQF_TRIGGER_FALLING, "freq", NULL);
	if (ret) {
		printk(KERN_ERR "%s: request_irq returned %d\n", __func__, ret);
		free_irq(freq_irq, NULL);
		goto fail;
	}

	misc_register(&freq_misc_device);

	printk(KERN_INFO "%s: gpio_pin=%d min_freq=%d max_freq=%d\n", __func__, gpio_pin, min_freq, max_freq);
	printk(KERN_INFO "%s: end\n", __func__);
	return ret;

fail:
	gpio_free(gpio_pin);
	return ret;
}

static void __exit freq_exit(void){
	printk(KERN_INFO "%s: start\n", __func__);

	misc_deregister(&freq_misc_device);
	free_irq(freq_irq, NULL);
	gpio_free(gpio_pin);

	printk(KERN_INFO "%s: end\n", __func__);
}

module_init(freq_init);
module_exit(freq_exit);

module_param(gpio_pin, int, S_IRUGO);
MODULE_PARM_DESC(gpio_pin, "GPIO input pin number for frequency measurement (default #DEFAULT_GPIO_PIN)");

module_param(min_freq, int, S_IRUGO);
MODULE_PARM_DESC(min_freq, "Minimum expected frequency to be measured (default #DEFAULT_MIN_FREQ)");

module_param(max_freq, int, S_IRUGO);
MODULE_PARM_DESC(max_freq, "Maximum expected frequency to be measured (default #DEFAULT_MAX_FREQ)");

MODULE_LICENSE("GPL");
MODULE_AUTHOR("Michael Johns <michaelwaynejohns@gmail.com>");
MODULE_DESCRIPTION("Frequency measurement device driver");
