/* Test fixture only: a tiny C file that mimics typical BMS model parameter styles. */
#ifndef MODEL_PARAMS_H
#define MODEL_PARAMS_H

#define CELL_CAP_AH        (5.0f)   /* nominal capacity */
#define DS_NEG_REF         3.3e-14  /* negative solid diffusivity */
#define EA_DS_NEG          30000.0
#define UV_THRESH_MV       2800

typedef struct {
    float Ds_p;      /* positive diffusivity */
    float k_n;       /* rate constant */
    float R0;        /* ohmic resistance */
    float x100;
} ModelParam_t;

#endif
