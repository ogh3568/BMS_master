/*
 * TEST FIXTURE ONLY - a deliberately small C model (OCV table + R0 + one RC + temperature
 * factor) used to test the SIL adapter and the inference math end to end. It stands in for
 * the user's C model in CI; it is not a battery model proposal.
 */
#include <math.h>

typedef struct {
    float r0;       /* ohmic resistance [Ohm] */
    float r1;       /* RC resistance [Ohm] */
    float tau1;     /* RC time constant [s] */
    float cap_ah;   /* capacity [Ah] */
    float ea_r;     /* activation energy of resistances [J/mol] */
} toy_param_t;

toy_param_t g_toy = { 0.020f, 0.015f, 30.0f, 5.0f, 20000.0f };
static float ocv_tbl[6] = { 3.00f, 3.45f, 3.62f, 3.80f, 4.00f, 4.20f };
float r_contact = 0.002f;
float unused_gain = 0.5f;   /* not used by the model: should be detected as insensitive */

static double s_soc, s_v1, s_v, s_i, s_temp;

static double ocv(double soc)
{
    double x = soc * 5.0;
    int k = (int)x;
    if (k < 0) k = 0;
    if (k > 4) k = 4;
    return ocv_tbl[k] + (ocv_tbl[k + 1] - ocv_tbl[k]) * (x - k);
}

void toy_reset(double soc0, double temp_c) { s_soc = soc0; s_v1 = 0.0; s_i = 0.0; s_temp = temp_c; }

void toy_step(double dt, double i, double temp_c)
{
    double f = exp(g_toy.ea_r / 8.314 * (1.0 / (temp_c + 273.15) - 1.0 / 298.15));
    double a = exp(-dt / g_toy.tau1);
    s_v1 = a * s_v1 + (1.0 - a) * g_toy.r1 * f * i;
    s_soc -= i * dt / (g_toy.cap_ah * 3600.0);
    s_i = i;
    s_temp = temp_c;
    s_v = ocv(s_soc) - s_v1 - i * (g_toy.r0 * f + r_contact);
}

double toy_voltage(void) { return s_v; }
double toy_soc(void) { return s_soc; }
