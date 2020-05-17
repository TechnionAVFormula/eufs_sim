/*
 * AMZ-Driverless
 * Copyright (c) 2018 Authors:
 *   - Juraj Kabzan <kabzanj@gmail.com>
 *   - Miguel de la Iglesia Valls <dmiguel@ethz.ch>
 *   - Manuel Dangel <mdangel@student.ethz.ch>
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the "Software"), to deal
 * in the Software without restriction, including without limitation the rights
 * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in all
 * copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
 * SOFTWARE.
 */

#include "vehicle_model.hpp"

namespace gazebo {
namespace fssim {

class KinematicBicycle: public VehicleModel {
public:
  KinematicBicycle(physics::ModelPtr &_model,
                   sdf::ElementPtr &_sdf,
                   boost::shared_ptr<ros::NodeHandle> &nh,
                   transport::NodePtr &gznode)
    : VehicleModel(_model, _sdf, nh, gznode)
  {}

private:
  virtual void updateState(const double dt) {
    double Fz = getNormalForce(state_);

    double alphaF = getSlipAngle();
    double alphaR = getSlipAngle(false);

    double FyF = getFrontFy(Fz);
    double FyR = getRearFy(Fz);

    // Drivetrain Model
    const double Fx   = getFx(state_, input_);
    const double M_Tv = getMTv(state_, input_);

    // Dynamics
    const auto x_dot_dyn  = f(state_, input_, Fx, M_Tv, FyF, FyR);
    const auto x_next_dyn = state_ + x_dot_dyn * dt;
    state_ = f_kin_correction(x_next_dyn, state_, input_, Fx, M_Tv, dt);
    state_.validate();
  }

  State f(const State &x,
                   const Input &u,
                   const double Fx,
                   const double M_TV,
                   const double FyF,
                   const double FyR) {
    const double FyF_tot = 2 * FyF;
    const double FyR_tot = 2 * FyR;
    const double v_x     = std::max(1.0, x.v_x);

    const double m_lon = param_.inertia.m + param_.driveTrain.m_lon_add;

    State x_dot{};
    x_dot.x   = std::cos(x.yaw) * x.v_x - std::sin(x.yaw) * x.v_y;
    x_dot.y   = std::sin(x.yaw) * x.v_x + std::cos(x.yaw) * x.v_y;
    x_dot.yaw = x.r;
    x_dot.v_x = (x.r * x.v_y) + (Fx - std::sin(u.delta) * (FyF_tot)) / m_lon;
    x_dot.v_y = ((std::cos(u.delta) * FyF_tot) + FyR_tot) / param_.inertia.m - (x.r * v_x);
    x_dot.r   = ((std::cos(u.delta) * FyF_tot * param_.kinematic.l_F
      + std::sin(u.delta) * (0/*FyF.left - FyF.right*/) * 0.5 * param_.kinematic.b_F)
      - ((FyR_tot) * param_.kinematic.l_R)
      + M_TV) / param_.inertia.I_z;
    x_dot.a_x = 0;
    x_dot.a_y = 0;

    return x_dot;
  }

  State f_kin_correction(const State &x_in,
                                  const State &x_state,
                                  const Input &u,
                                  const double Fx,
                                  const double M_TV,
                                  const double dt) {
    State        x       = x_in;
    const double v_x_dot = Fx / (param_.inertia.m + param_.driveTrain.m_lon_add);
    const double v       = std::hypot(state_.v_x, state_.v_y);
    const double v_blend = 0.5 * (v - 1.5);
    const double blend   = std::fmax(std::fmin(1.0, v_blend), 0.0);

    x.v_x = blend * x.v_x + (1.0 - blend) * (x_state.v_x + dt * v_x_dot);

    const double v_y = std::tan(u.delta) * x.v_x * param_.kinematic.l_R / param_.kinematic.l;
    const double r   = std::tan(u.delta) * x.v_x / param_.kinematic.l;

    x.v_y = blend * x.v_y + (1.0 - blend) * v_y;
    x.r   = blend * x.r + (1.0 - blend) * r;
    return x;
  }

  double getFx(const State &x, const Input &u) {
    const double dc = x.v_x <= 0.0 && u.dc < 0.0 ? 0.0 : u.dc;
    const double Fx = dc * param_.driveTrain.cm1 - getFdrag(x) - param_.driveTrain.cr0;
    return Fx;
  }

  double getMTv(const State &x, const Input &u) const {
    const double shrinkage = param_.torqueVectoring.shrinkage;
    const double K_stab    = param_.torqueVectoring.K_stability;
    const double l         = param_.kinematic.l;

    const double delta = u.delta;
    const double v_x   = x.v_x;

    return 0.0;
  }

  double getNormalForce(const State &x) {
    return param_.inertia.g * param_.inertia.m + getFdown(x);
  }

  double getFdown(const State &x) {
    return param_.aero.c_down * x.v_x * x.v_x;
  }

  double getFdrag(const State &x) {
    return param_.aero.c_drag * x.v_x * x.v_x;
  }

  double getFrontFy(const double Fz) {
    double slipAngle = getSlipAngle();

    const double Fz_axle = getDownForceFront(Fz);

    const double B    = param_.tire.B;
    const double C    = param_.tire.C;
    const double D    = param_.tire.D;
    const double E    = param_.tire.E;
    const double mu_y = D * std::sin(C * std::atan(B * (1.0 - E) * slipAngle + E * std::atan(B * slipAngle)));
    const double Fy   = Fz_axle * mu_y;
    return Fy;
  }

  double getRearFy(const double Fz) {
    double slipAngle = getSlipAngle(false);

    const double Fz_axle = getDownForceFront(Fz);

    const double B    = param_.tire.B;
    const double C    = param_.tire.C;
    const double D    = param_.tire.D;
    const double E    = param_.tire.E;
    const double mu_y = D * std::sin(C * std::atan(B * (1.0 - E) * slipAngle + E * std::atan(B * slipAngle)));
    const double Fy   = Fz_axle * mu_y;
    return Fy;
  }

  double getDownForceFront(const double Fz) {
      double FzAxle = 0.5 * param_.kinematic.w_front * Fz;
      return FzAxle;
  }

  double getDownForceRear(const double Fz) {
      double FzAxle = 0.5 * (1 - param_.kinematic.w_front) * Fz;
      return FzAxle;
  }
};

} // namespace fssim
} // namespace gazebo
