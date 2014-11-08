# -*- coding: utf-8 -*-
from modules import (RailwayNetworkBuilder, RoadwayNetworkBuilder,
                     RailwayNetworkCost, RailwayReport, RoadwayReport)
from pprint import pprint
import math

"""
    This module is used by freight_network. It exposes classes for the two
    modal networks that compose a FreightNetwork class (RailwayNetwork and
    RoadwayNetwork).
"""


class BaseModalNetwork(object):

    """Represents a generic modal network.

    This class must be subclassed to represent a specific modal network.
    RailwayNetwork or RoadwayNetwork are modal networks.

    A freight transport modal network has origin-destination pairs that
    represent tons being carried from origin to destination. Each od pair uses
    a path wich is a sequence of links.

    The main costs of transport network are those of mobility and
    infrastructure. Subclassed modal networks provide methods to cost mobility
    (attached mainly to od pairs characteristics) and infrastructure
    (attached mainly to links characteristics).

    A modal network has 5 main data members:
        1. params: parameters of the network used in calculations
        2. od_pairs: od_pairs using the network
        3. links: links available to od pair paths
        4. paths: paths for all possible od pairs in the network
        5. costs: mobility and infrastructure costs of the network
    """

    def __init__(self):

        self.params = {}
        self.od_pairs = {}
        self.links = {}
        self.paths = {}
        self.costs = {"mob": None, "inf": None}

    def __iter__(self):
        return self.iter_links()

    # PUBLIC
    # iters
    def iter_od_pairs(self, limit=None):
        """Iterate od pairs with an optional limit in number of results."""

        counter = 0
        for od_pair in self.od_pairs.values():
            for od_pair_category in od_pair.values():

                # check if limit is reached
                if limit and counter >= limit:
                    break
                counter += 1

                yield od_pair_category

    def iter_links(self, limit=None):
        """Iterate links with an optional limit in number of results."""

        counter = 0
        for link in self.links.values():
            for link_gauge in link.values():

                # check if limit is reached
                if limit and counter >= limit:
                    break
                counter += 1

                yield link_gauge

    # getters
    def get_path(self, od):
        return self.paths[od.get_id()]

    def get_path_distance(self, od):
        """Get distance of a path.

        Args:
            od: od pair wich path we are looking its distance
        """

        if od.is_intrazone():
            return 0.0
        else:
            return self.get_path(od).calc_distance(self.get_links())

    def get_links(self):
        return self.links

    def get_link(self, id_link):
        return self.links[id_link]

    def get_total_ton_km(self):
        """Sum all ton_km from all od_pairs used in the model."""
        total_tk_link = 0.0
        total_tk_od = 0.0

        # iterate through all links adding ton * dist
        for link in self.links.values():
            for link_gauge in link.values():
                total_tk_link += link_gauge.get_ton() * link_gauge.get_dist()

        # iterate throught all ods adding ton * dist
        for od in self.iter_od_pairs():
            total_tk_od += od.get_ton() * od.get_dist()

        # control that both ways of calculate total_ton_km are the same!
        msg = "Link and OD based ways of total_ton_km calculation differ."
        assert abs(total_tk_link / total_tk_od - 1) < 0.001, msg

        return total_tk_link

    def get_od(self, id_od, category_od):
        """Returns existent od pair or create a new one if it doesn't exist.

        Args:
            id_od: the origin-destination id (eg. "1-3")
            category_od: the railway category of the freight transported.
        """

        # check if od pair is in the network
        if id_od not in self.od_pairs:
            self._create_od_pair(id_od, category_od)

        # check if od pair has the category asked
        if category_od not in self.od_pairs[id_od]:
            self._create_od_pair(id_od)

        return self.od_pairs[id_od][category_od]

    def get_total_tons(self):
        """Sum all tons from od_pairs used in the model."""
        total_tons = 0.0

        # iterate through all od pairs adding its tons
        for od in self.iter_od_pairs():
            total_tons += od.get_ton()

        return total_tons

    # reports
    def print_objects_report(self):
        """Print report with examples of objects inside RailwayNetwork."""

        # create report object
        rep = self.REPORT_CLASS()

        # ask for excel report passing RailNetwork object itself
        rep.print_objects_report(self)

    def report_to_excel(self, xl_report=None):
        """Make a report of modal network results in excel."""

        # create report object
        rep = self.REPORT_CLASS(xl_report)

        # ask for excel report passing RailNetwork object itself
        rep.report_to_excel(self)

    # PRIVATE
    def _create_od_pair(self, id_od, category_od):
        network_builder = self.BUILDER_CLASS()
        network_builder.create_od_pair(self, id_od, category_od)


class RoadwayNetwork(BaseModalNetwork):

    """Represents a road network with methods to cost it.

    RoadwayNetwork() starts an empty network and it uses RoadwayNetworkBuilder
    to build an instance."""

    REPORT_CLASS = RoadwayReport
    BUILDER_CLASS = RoadwayNetworkBuilder

    def __init__(self):

        self.trucks = None
        super(RoadwayNetwork, self).__init__()

        # build network
        network_builder = self.BUILDER_CLASS()
        network_builder.build(self)


class RailwayNetwork(BaseModalNetwork):

    """Represents a rail network with methods to cost it.

    RailwayNetwork() starts an empty network and it uses RailwayNetworkBuilder
    to build an instance.
    """

    REPORT_CLASS = RailwayReport
    BUILDER_CLASS = RailwayNetworkBuilder

    def __init__(self):

        self.wagons = None
        self.locoms = None
        super(RailwayNetwork, self).__init__()

        # build network
        network_builder = self.BUILDER_CLASS()
        network_builder.build(self)

    # PUBLIC
    def has_railway_path(self, od):
        """Check if an od pair has an operable railway path.

        Args:
            od: od pair to be evaluated to has a railway path or not
        """

        # check if od is in paths
        if not od.get_id() in self.paths:
            return False

        # check the path is operable by railway
        path = self.paths[od.get_id()].get_path()
        gauge = self.paths[od.get_id()].get_gauge()

        has_path_and_gauge = bool(path and gauge)
        has_links = "-" in path

        return has_path_and_gauge and has_links

    def calc_simple_mobility_cost(self):
        """Calculates mobility cost of running each origin-destination rail
        service independently."""

        # iterate through all od pairs
        for od in self.iter_od_pairs():

            # calculate mobility requirements to run rail service for od
            self._calculate_mobility_od(od)

        # calculate and store mobility costs for all mobility requirements
        self.costs["mob"] = self._calc_mobility_cost()

    def calc_optimized_mobility_cost(self):
        """Regroup trains operating below maximum capacity.

        Check if regrouping trains in a single link is more cost-effective than
        previous situation, where some trains where operating below their
        maximum capacity. If its not the case, revert regrouping."""

        # iterate through all links
        for link in self.links.values():
            for link_gauge in link.values():

                # store current cost of network
                current_cost = self._calc_mobility_cost()["total_mobility"]

                # calculate locomotives that can be eliminated
                idle_capacity = link_gauge.idle_capacity
                loc_capacity = self.params["locomotive_capacity"].value
                idle_locs = math.floor(float(idle_capacity) /
                                       float(loc_capacity))

                # regroup link
                self._regroup_link(link_gauge, idle_locs)

                # calculate new cost with link regrouped
                new_cost = self._calc_mobility_cost()["total_mobility"]

                # if new cost is not lower, revert regroup of link
                # if False:
                if new_cost >= current_cost:
                    self._revert_regroup_link(link_gauge, idle_locs)

        # calculate and store mobility costs
        self.costs["mob"] = self._calc_mobility_cost()

    def calc_infrastructure_cost(self):
        """Calculate infrastructure costs."""

        # calculate and store infrastructure costs
        self.costs["inf"] = self._calc_infrastructure_cost()

    def links_by_od_to_excel(self, xl_links_by_od=None):
        """Write table of links by possible od pair to excel."""

        # create report object
        rep = RailwayReport()

        # ask for excel report passing RailNetwork object itself
        rep.links_by_od_to_excel(self.paths, xl_links_by_od)

    # REPORT methods
    def print_costs_report(self):
        """Print only costs report of RailwayNetwork."""

        # create report object
        rep = RailwayReport()

        # ask for excel report passing RailNetwork object itself
        rep.print_complete_report(self)

    # PRIVATE
    def _calc_infrastructure_cost(self):
        """Calculates infrastructure cost for current mobility requirements.

        Creates a railway NetworkCost() object to cost infrastructure for a
        network described by current parameters, locomotives, wagons and
        links data."""

        # create a railway network cost object
        network_cost = RailwayNetworkCost(self.params, self.locoms,
                                          self.wagons, self.links)

        return network_cost.cost_infrast()

    def _calc_mobility_cost(self):
        """Calculates mobility cost for current mobility requirements.

        Creates a railway NetworkCost() object to cost mobility for a network
        described by current parameters, locomotives, wagons and links data."""

        # create a railway network cost object
        network_cost = RailwayNetworkCost(self.params, self.locoms,
                                          self.wagons, self.links)

        return network_cost.cost_mobility()

    def _calculate_mobility_od(self, od):
        """Takes an OD object and calculate its mobility requirements.

        Update the rolling material objects (wagons and locomotives) with the
        new freight service required (od pair) object and the links used by od
        pair route with the idle remaining freight transport capacity in
        locomotives.

        Args:
            od: OD pair with tons to be carried by rolling material
        """

        # wagons mobility
        self.wagons.add_freight_service(od.get_ton(), od.get_dist())

        # locomotives mobility
        idle_capacity_l = self.locoms.add_freight_service(od.get_ton(),
                                                          od.get_dist())

        # add idle capacity of locomotives along the route used by od pair
        exception_counter = 0
        MAX_EXCEPTIONS = 50
        for link in od.links:

            assert exception_counter < MAX_EXCEPTIONS, "Too many error paths."

            # try to update tons and idle capacity of link-gauge
            try:
                self.links[link][od.gauge].add_idle_cap(idle_capacity_l)

            # if impossible, there is no link-gauge in the network for od_pair
            except:
                exception_counter += 1
                print "".join(("There is no link ", link, " and gauge ",
                               od.gauge, " for od pair ", od.id,
                               " with path: ", od.path))

    def _regroup_link(self, link, idle_locs):
        """Eliminate some idleness in a link regrouping trains.

        Args:
            link: a link width idle capacity in trains to be regrouped to save
                locomotives
            idle_locs: number of idle locomotives
        """

        # store parameters to be used in short variables
        loc_capacity = self.params["locomotive_capacity"].value
        wagon_capacity = self.params["wagon_capacity"].value

        # calcualte wagons regrouped
        wagons_regrouped = idle_locs * loc_capacity / wagon_capacity

        # update idle_capacity of link
        link.regroup(idle_locs * loc_capacity)

        # update rolling material time requirements
        self.locoms.regroup(idle_locs, link.get_dist())
        self.wagons.add_regroup_time(wagons_regrouped)

    def _revert_regroup_link(self, link, idle_locs):
        """Revert previously regrouping of trains restoring idleness.

        Args:
            link: a previously regrouped link that has eliminated some idleness
            idle_locs: number of idle locomotives
        """

        # store parameters to be used in short variables
        loc_capacity = self.params["locomotive_capacity"].value
        wagon_capacity = self.params["wagon_capacity"].value

        # calcualte wagons regrouped
        wagons_regrouped = idle_locs * loc_capacity / wagon_capacity

        # update idle_capacity of link
        link.revert_regroup(idle_locs * loc_capacity)

        # update rolling material time requirements
        self.locoms.revert_regroup(idle_locs, link.dist)
        self.wagons.subtract_regroup_time(wagons_regrouped)


def test_railway_network():

    # initiate object
    rn = RailwayNetwork()
    # rn.links_by_od_to_excel()
    rn.print_objects_report()

    # CALCULATE SIMPLE MOBILITY COSTS and its INFRASTRUCTURE COSTS
    print "\n***********************************"
    print "Calculate simple mobility cost."
    print "***********************************"
    rn.calc_simple_mobility_cost()

    print "\n***Mobility cost results***\n"
    pprint(rn.costs["mob"])

    print "\n***Wagons results***"
    print rn.wagons

    print "\n***Locomotives results***"
    print rn.locoms

    print "\n***Global results***\n"
    print "total tons", "{:,.2f}".format(rn.get_total_tons())
    print "total ton-km", "{:,.2f}".format(rn.get_total_ton_km())
    print "average distance", rn.get_total_ton_km() / rn.get_total_tons()
    print "rejected tons", "{:,.2f}".format(rn.get_rejected_tons())

    # print "\n***Idle capacity by link***"
    # for gauge in rn.links.values():
    #     for link in gauge.values():
    #         print str(link.id).ljust(10), \
    #               "{:,.1f}".format(link.idle_capacity).ljust(15), link.gauge

    # print rn.od_pairs["41-84"].has_path()

    print "\n***********************************"
    print "Calculate infrastructure cost."
    print "***********************************"
    rn.calc_infrastructure_cost()

    print "\n***infrastructure cost results***\n"
    pprint(rn.costs["inf"])

    # MAKE REPORT
    rn.report_to_excel("reports/report_simple_mobility.xlsx")

    # CALCULATE OPTIMIZED MOBILITY COSTS and its INFRASTRUCTURE COSTS
    print "\n***********************************"
    print "Calculate optimized mobility cost."
    print "***********************************"
    rn.calc_optimized_mobility_cost()

    print "\n***Mobility cost results***\n"
    pprint(rn.costs["mob"])

    print "\n***Wagons results***"
    print rn.wagons

    print "\n***Locomotives results***"
    print rn.locoms

    print "\n***Global results***\n"
    print "total tons", "{:,.2f}".format(rn.get_total_tons())
    print "total ton-km", "{:,.2f}".format(rn.get_total_ton_km())
    print "average distance", rn.get_total_ton_km() / rn.get_total_tons()
    print "rejected tons", "{:,.2f}".format(rn.get_rejected_tons())

    print "\n***********************************"
    print "Calculate infrastructure cost."
    print "***********************************"
    rn.calc_infrastructure_cost()

    print "\n***infrastructure cost results***\n"
    pprint(rn.costs["inf"])

    # MAKE REPORT
    rn.report_to_excel("reports/report_optimized_mobility.xlsx")


def test_roadway_network():

    road = RoadwayNetwork()
    print road.get_total_tons()
    print road.get_total_ton_km()
    road.print_objects_report()


if __name__ == '__main__':

    print "\n*****MANUAL TEST OF RAILWAY NETWORK*****\n"
    test_railway_network()

    print "\n*****MANUAL TEST OF ROADWAY NETWORK*****\n"
    test_roadway_network()
