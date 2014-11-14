class BaseNetworkCost(object):

    def __init__(self, rn):
        self.rn = rn
        self.total_ton_km = self.rn.get_total_ton_km()


class RailwayNetworkCost(BaseNetworkCost):

    # PUBLIC
    def cost_mobility(self):
        """Calculate each type of mobility cost."""
        RV = {}

        # fill RV with moblity costs per ton-km
        RV["eac_wagon"] = self._cost_eac_wagon()
        RV["eac_locom"] = self._cost_eac_locom()
        RV["fuel_and_lub"] = self._cost_fuel_and_lub()
        RV["maintenance"] = self._cost_mobility_maintenance()
        RV["manpower"] = self._cost_manpower()

        # sum all costs and add it to total mobility
        RV["total_mobility"] = sum(RV.values())

        return RV

    def cost_infrast(self):
        """Calculate each type of infrastructure cost."""

        # initialize return value
        RV = {}
        RV["eac_detour"] = 0
        RV["eac_track"] = 0
        RV["maintenance"] = 0

        # take parameters
        wagon_capacity = self.rn.params["wagon_capacity"].value
        wagon_weight = self.rn.params["wagon_weight"].value
        locomotive_capacity = self.rn.params["locomotive_capacity"].value
        locomotive_weight = self.rn.params["locomotive_weight"].value

        # calculate gross ton_km and infrastructure cost for each link
        for link in self.rn.iter_links():

            # check if there is load on that link
            if link.get_ton() > 0:

                # calculate gross ton-km carried by the link
                gross_tk = link.get_gross_ton_km(wagon_capacity,
                                                 wagon_weight,
                                                 locomotive_capacity,
                                                 locomotive_weight)

                # calculate costs of link infrastructure
                eac_detour = self._cost_detour(gross_tk, link.get_dist())
                eac_track = self._cost_eac_track(gross_tk, link.get_dist())
                maintenance = self._cost_infrast_maint(
                    gross_tk, link.get_dist())

                # update RV cost category with traffic of the link
                RV["eac_detour"] += eac_detour
                RV["eac_track"] += eac_track
                RV["maintenance"] += maintenance

                # write costs to link object
                link.eac_detour = eac_detour
                link.eac_track = eac_track
                link.maintenance = maintenance

        # divide all costs to express them in terms of ton-km
        for infrast_cost in RV:
            if self.total_ton_km > 0.1:
                RV[infrast_cost] = RV[infrast_cost] / self.total_ton_km
            else:
                RV[infrast_cost] = 0.0

        # sum all costs and add it to total mobility
        RV["total_infrastructure"] = sum(RV.values())

        return RV

    # PRIVATE
    # *** cost MOBILITY methods ***
    def _cost_eac_ton_km(self, eac, units):
        """Calculate eac by ton_km for a number of units."""

        # calculate year cost
        year_eac = eac * units

        # calculate cost per ton_km
        if self.total_ton_km > 0.1:
            eac_ton_km = year_eac / self.total_ton_km

        else:
            eac_ton_km = 0.0

        return eac_ton_km

    def _cost_eac_wagon(self):
        """Calculate eac by ton_km of wagons."""

        # assign parameters to short variables
        wagon_eac = self.rn.params["wagon_eac"].value
        num_wagons = self.rn.wagons.get_units_needed_by_time()
        # print "wagon", wagon_eac, num_wagons

        return self._cost_eac_ton_km(wagon_eac, num_wagons)

    def _cost_eac_locom(self):
        """Calculate eac by ton_km of locomotives."""

        # assign parameters to short variables
        locom_eac = self.rn.params["locomotive_eac"].value
        num_locoms = self.rn.locoms.get_units_needed_by_time()
        # print "locomotive", locom_eac, num_locoms

        return self._cost_eac_ton_km(locom_eac, num_locoms)

    def _cost_fuel_and_lub(self):
        """Calculate cost of fuel and lubricant by ton_km."""

        # assign parameters to short variables
        fuel_by_km = self.rn.params["fuel_cost_by_km"].value
        loc_average_haul = self.rn.locoms.get_average_haul()
        num_locoms = num_locoms = self.rn.locoms.get_units_needed_by_time()
        lub_fuel_ratio = self.rn.params["lubricants_fuel_ratio"].value

        # calculate fuel_ton_km cost
        if self.total_ton_km > 0.1:
            fuel_ton_km = fuel_by_km * loc_average_haul * \
                num_locoms / self.total_ton_km

        else:
            fuel_ton_km = 0.0

        # calculate lubricant ton km cost
        lub_ton_km = fuel_ton_km * lub_fuel_ratio

        return fuel_ton_km + lub_ton_km

    def _cost_mobility_maintenance(self):
        """Calcualate cost of locomotives and wagons maintenance by ton_km."""

        if self.total_ton_km > 0.1:

            # calculate locmotives maintenance by ton_km
            locom_maintenance = self.rn.params["maintenance_by_locomotive"].value * \
                self.rn.locoms.get_units_needed_by_time() / self.total_ton_km

            # calculate wagon maintenance by ton_km
            wagon_maintenance = self.rn.params["maintenance_by_wagon"].value * \
                self.rn.wagons.get_units_needed_by_time() / self.total_ton_km

        else:
            locom_maintenance = 0.0
            wagon_maintenance = 0.0

        return locom_maintenance + wagon_maintenance

    def _cost_manpower(self):
        """Calculate cost of manpower on board of train."""

        # assign parameters to short variables
        cost_by_hour = self.rn.params["manpower_cost_by_loc_hour"].value

        # calculate locomotive hours with manpower on the train
        operation_hours = self.rn.locoms.get_operation_time()

        if self.total_ton_km > 0.1:
            manpower_cost = cost_by_hour * operation_hours / self.total_ton_km

        else:
            manpower_cost = 0.0

        return manpower_cost

    # *** cost INFRASTRUCTURE methods ***
    def _cost_detour(self, gross_tk, dist):
        """Calculate equivalent annual cost of detours."""

        # calculate number of detours needed
        num_detours = self._calc_number_of_detours(gross_tk, dist)

        # calculate wages cost to maintain detours
        wages_by_detour = self.rn.params["yearly_wages_by_turnout"].value
        total_wages_cost = num_detours * wages_by_detour

        # calculate eac of detour tracks
        density = gross_tk / dist
        total_eac_cost = num_detours * self._cost_eac_track(density, 1.0)

        return total_wages_cost + total_eac_cost

    def _calc_number_of_detours(self, gross_tk, dist):
        """Calculate number of detours needed in a certain track."""

        # store parameters in short-name variables
        max_turnout_distance = self.rn.params["turnout_freq"].value
        max_turnout_density = self.rn.params["turnout_freq_max_density"].value
        t_distance = max_turnout_distance

        # calculate density
        density = gross_tk / dist

        if not density < max_turnout_density:
            t_distance = max_turnout_distance / (density / max_turnout_density)

        num_detours = dist / t_distance

        return num_detours

    def _cost_eac_track(self, gross_tk, dist):
        """Calculate equivalent annual cost of track.

        If its a main track, calculate EAC cost of track. If its a secondary
        track, there is no eac cost of track."""

        # check if is a main track
        if self._is_main_track(gross_tk, dist):

            # store parameters in short-name variables
            a_eac = self.rn.params["coef_a_track_cost"].value
            b_eac = self.rn.params["coef_b_track_cost"].value
            use_life = self.rn.params["useful_life_track"].value
            max_gross_tk = self.rn.params["gross_tk_in_hq_track_lifetime"].value
            int_rate = self.rn.params["interest_rate"].value
            max_cost_track = self.rn.params["high_quality_track_price"].value

            # calculate gross tk in max possible useful life years
            gross_tk_in_use_life = use_life * gross_tk / dist

            # use estimated function if gross_tk expected is less than maximum
            if gross_tk_in_use_life < max_gross_tk:
                cost_track = a_eac + b_eac * gross_tk_in_use_life

            # otherwise, use high quality track price and recalculate use_life
            else:
                cost_track = max_cost_track
                use_life = max_gross_tk / (gross_tk / dist)

            # calculate eac by year
            crf = self._capital_recovery_factor(int_rate, use_life)
            eac = cost_track * crf * dist

        else:
            eac = 0.0

        return eac

    def _cost_infrast_maint(self, gross_tk, dist):
        """Calculate cost of maintaining infrastructure."""

        # track maintenance cost calculation
        a_track = self.rn.params["coef_a_track_maint_cost"].value
        b_track = self.rn.params["coef_b_track_maint_cost"].value
        track_maint = ((gross_tk / dist) ** a_track) * b_track * gross_tk

        # no track maintenance cost calculation
        a_notrack = self.rn.params["coef_a_notrack_maint_cost"].value
        b_notrack = self.rn.params["coef_b_notrack_maint_cost"].value
        no_track_maint = ((gross_tk / dist) ** a_notrack) * \
            b_notrack * gross_tk

        return track_maint + no_track_maint

    def _is_main_track(self, gross_tk, dist):
        """Check if this is a main track.

        If net tons density (ton-km/km) goes below a certain threshold, this is
        a secondary track. If density goes above the threshold, is a main
        track."""

        # store parameters in short-name variables
        net_to_gross = self.rn.params["net_to_gross_factor"].value
        main_min_density = self.rn.params["main_min_density"].value

        # calculate net ton-km
        net_tk = gross_tk / net_to_gross

        # calculate density
        density = net_tk / dist

        return density > main_min_density

    def _capital_recovery_factor(self, int_rate, use_life):
        """Calculate capital recovery factor."""

        a = int_rate * pow(1 + int_rate, use_life)
        b = pow(1 + int_rate, use_life) - 1

        return a / b


class RoadwayNetworkCost(BaseNetworkCost):

    # PUBLIC
    def cost_mobility(self):
        """Calculate each type of mobility cost."""
        RV = {}

        # sum all costs and add it to total mobility
        RV["total_mobility"] = self._cost_mobility()

        return RV

    def cost_infrast(self):
        """Calculate each type of infrastructure cost."""
        RV = {}
        RV["eac_track"] = 0

        # calculate gross ton_km and infrastructure cost for each link
        for link in self.rn.iter_links():

            # check if there is load on that link
            if link.get_ton() > 0:

                # calculate costs of link infrastructure
                eac_track = self._cost_eac_track(link.get_ton(),
                                                 link.get_dist())

                # update RV cost category with traffic of the link
                RV["eac_track"] += eac_track

                # write costs to link object
                link.eac_track = eac_track

        # divide all costs to express them in terms of ton-km
        for infrast_cost in RV:
            RV[infrast_cost] = RV[infrast_cost] / self.total_ton_km

        # sum all costs and add it to total mobility
        RV["total_infrastructure"] = sum(RV.values())

        return RV

    # PRIVATE
    def _cost_mobility(self):
        """Calculate cost of truck mobility."""

        mobility_cost_tk = self.rn.params["mobility_cost_tk"].value
        mobility_cost = self.rn.get_total_ton_km() * mobility_cost_tk

        return mobility_cost / self.total_ton_km

    def _cost_eac_track(self, ton, dist):
        """Calculate equivalent annual cost of track."""

        a_eac = self.rn.params["coef_a_infrast_cost"].value
        b_eac = self.rn.params["coef_b_infrast_cost"].value

        eac = b_eac * (ton ** a_eac)

        return eac * dist


def test():

    print "\nTest Case 1: mobility cost"
    print "-----------"

    # set up all objects to pass to NetworkCost
    from railway_parameters import Parameter
    params = {"wagon_eac": Parameter("wagon_eac", 6463.8),
              "locomotive_eac": Parameter("locomotive_eac", 154445.9),
              "fuel_cost_by_km": Parameter("fuel_cost_by_km", 2),
              "lubricants_fuel_ratio": Parameter("lubricants_fuel_ratio", 0.0667),
              "maintenance_by_locomotive": Parameter("maintenance_by_locomotive", 100170),
              "maintenance_by_wagon": Parameter("maintenance_by_wagon", 2487.6),
              "manpower_cost_by_loc_hour": Parameter("manpower_cost_by_loc_hour", 30.42)}

    from railway_rolling_material import RollingMaterial
    locoms = RollingMaterial()
    locoms.running = 137.91 * 1564.29
    locoms.idle_heads = 137.91 * 30 * 125.14
    locoms.idle_turnout = 137.91 * 1250.14
    locoms.speed = 40  # (km/h)
    locoms.availability = 6570  # (hr/year)
    locoms.capacity = 2400  # (ton)
    locoms.head_stops_time = 15  # (hr/head_stop)
    locoms.turnout_time = 4  # (hr/turnout_stop)
    locoms.turnout_freq = 200  # (km between turnouts

    wagons = RollingMaterial()
    wagons.running = 15313.81 * 535.33
    wagons.idle_heads = 15313.81 * 180 * 42.83
    wagons.idle_turnout = 15313.81 * 428.27
    wagons.speed = 40  # (km/h)
    wagons.availability = 8672  # (hr/year)
    wagons.capacity = 60  # (ton)
    wagons.head_stops_time = 15  # (hr/head_stop)
    wagons.turnout_time = 4  # (hr/turnout_stop)
    wagons.turnout_freq = 200  # (km between turnouts

    from railway_link import Link
    link = Link("1-3", 500, "ancha")
    link.ton = 22036200
    links = {"1-3": {"ancha": link}}

    from pprint import pprint
    pprint(NetworkCost(params, locoms, wagons, links).cost_mobility())
    print "\nlocoms", locoms
    print "\nwagons", wagons

if __name__ == '__main__':
    test()