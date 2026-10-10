import pandas as pd

import streamlit as st

from services.demo_data import demo_properties

from services.parser import parse_requirements, STATE_ALIASES

from services.ranking import rank_properties

from services.rentcast import RentCastError, search_rentals
from services.llm_service import extract_rental_requirements
import traceback

st.set_page_config(page_title="RentLense", page_icon="🏠", layout="wide")

st.title("🏠 RentLens")

st.caption("An Intelligent System for Finding the Right Rental Property")

DEFAULT_QUERY = (

    "I need a 2-bedroom apartment in Austin, Texas below $3000 per month "

    "with parking and security."

)

with st.sidebar:

    st.header("Search preferences")

    query = st.text_area("Describe your ideal rental", DEFAULT_QUERY, height=130)

    use_demo = st.toggle("Use demo data", value=True)
    use_groq = st.toggle("Use Groq AI", value=True)

    top_k = st.slider("Number of results", min_value=1, max_value=20, value=8)

    st.divider()

    st.caption("Demo mode uses a small built-in dataset and needs no API key.")

def money(value):

    if value is None or pd.isna(value):

        return "N/A"

    return f"${float(value):,.0f}/month"

def show_property(row):
    address = row.get("formattedAddress")

    if address is None or pd.isna(address) or not str(address).strip():
        address = "Address not provided"

    #with st.container(border=True):
        c1, c2 = st.columns([4, 1])

        with c1:
            st.subheader(address)
            st.write(
                f"**{row.get('propertyType', 'Unknown')}** · "
                f"{row.get('bedrooms', 'N/A')} bed · "
                f"{row.get('bathrooms', 'N/A')} bath · "
                f"{money(row.get('price'))}"
            )

        with c2:
            st.metric(
                "Match",
                f"{float(row.get('match_score', 0)):.0f}%"
            )

    with st.container(border=True):

        c1, c2 = st.columns([4, 1])

        with c1:

            st.subheader(address)

            st.write(

                f"**{row.get('propertyType', 'Unknown')}** · "

                f"{row.get('bedrooms', 'N/A')} bed · "

                f"{row.get('bathrooms', 'N/A')} bath · "

                f"{money(row.get('price'))}"

            )

        with c2:

            st.metric("Match", f"{float(row.get('match_score', 0)):.0f}%")

        details = []

        if pd.notna(row.get("squareFootage")):

            details.append(f"Size: {float(row['squareFootage']):,.0f} sq ft")

        if pd.notna(row.get("yearBuilt")):

            details.append(f"Built: {int(row['yearBuilt'])}")

        if row.get("status"):

            details.append(f"Status: {row['status']}")

        if details:

            st.caption(" · ".join(details))

        # Additional cost transparency

        with st.expander("💰 Additional costs and estimated total", expanded=False):

            def find_cost(*field_names):

                for field in field_names:

                    value = row.get(field)

                    if value is not None and pd.notna(value):

                        try:

                            return float(value)

                        except (TypeError, ValueError):

                            continue

                return None

            rent = find_cost("price")

            deposit = find_cost("securityDeposit", "security_deposit")

            application_fee = find_cost("applicationFee", "application_fee")

            parking_fee = find_cost("parkingFee", "parking_fee", "parkingCost")

            pet_fee = find_cost("petFee", "pet_fee")

            st.write("**Advertised monthly rent:**",

                     f"${rent:,.2f}" if rent is not None else "Not provided")

            st.write("**Security deposit:**",

                     f"${deposit:,.2f}" if deposit is not None else "Not provided")

            st.write("**Application fee:**",

                     f"${application_fee:,.2f}" if application_fee is not None else "Not provided")

            st.write("**Parking fee:**",

                     f"${parking_fee:,.2f}/month" if parking_fee is not None else "Not provided")

            st.write("**Pet fee:**",

                     f"${pet_fee:,.2f}" if pet_fee is not None else "Not provided")

            if rent is not None and parking_fee is not None:

                st.metric(

                    "Rent + known monthly parking fee",

                    f"${rent + parking_fee:,.2f}/month"

                )

            elif rent is not None:

                st.metric("Advertised rent", f"${rent:,.2f}/month")

                st.caption(

                    "Other monthly costs are not included because their amounts "

                    "have not been confirmed."

                )

            if rent is not None and deposit is not None and application_fee is not None:

                st.metric(

                    "Known initial cost (rent + deposit + application fee)",

                    f"${rent + deposit + application_fee:,.2f}"

                )

            st.caption(

                "Missing fees are marked 'Not provided'. These figures are "

                "estimates based only on available listing data; other charges may apply."

            )

        
        
        reasons = row.get("match_reasons", [])
        breakdown = row.get("score_breakdown", {})

        if (isinstance(reasons, list) and reasons) or breakdown:
            with st.expander("🔎 Why this property matches", expanded=False):

                if isinstance(reasons, list) and reasons:
                    st.markdown("**Matching reasons**")
                    for reason in reasons:
                        st.write(f"✓ {reason}")

                if breakdown:
                    st.markdown("**Match score breakdown**")
                    breakdown_df = pd.DataFrame(
                        [
                            {
                                "Requirement": key,
                                "Points": round(value, 1),
                            }
                            for key, value in breakdown.items()
                        ]
                    )
                    st.dataframe(
                        breakdown_df,
                        hide_index=True,
                        use_container_width=True,
                    )



if st.button(
    "🔎 Find matching properties",
    type="primary",
    use_container_width=True,
):
    if not query.strip():
        st.warning("Please describe the rental property you want.")
        st.stop()

    try:
        # Step 1: Parse the request with the existing local parser.
        # This gives us RentLense's expected field names.
        requirements = parse_requirements(query)

        
        # Step 2: Optionally improve interpretation with Groq.
        if use_groq:
            try:
                with st.spinner(
                    "Groq AI is understanding your rental request..."
                ):
                    ai_requirements = extract_rental_requirements(query)

                if not isinstance(ai_requirements, dict):
                    raise ValueError(
                        "Groq returned an unexpected response format."
                    )

                # Update fields only when Groq supplies a value.
                for field in (
                    "city",
                    "bedrooms",
                    "bathrooms",
                    "parking",
                    "security",
                    "zipCode",
                ):
                    value = ai_requirements.get(field)
                    if value is not None:
                        requirements[field] = value

                # Normalize the state.
                state = ai_requirements.get("state")
                if isinstance(state, str) and state.strip():
                    state = state.strip()
                    requirements["state"] = STATE_ALIASES.get(
                        state.lower(), state.upper()
                    )

                
                # Use the monthly budget returned by Groq.
                monthly_budget = ai_requirements.get("max_monthly_rent")

                if monthly_budget is None:
                  monthly_budget = ai_requirements.get("max_price")

                if monthly_budget is not None:
                  requirements["max_price"] = float(monthly_budget)
                

                # Accept either property-type key.
                property_type = ai_requirements.get(
                    "propertyType",
                    ai_requirements.get("property_type"),
                )
                if property_type:
                    requirements["propertyType"] = property_type

                requirements["raw_query"] = query

                st.success("Groq AI processed your rental request.")

            except Exception as groq_error:
                st.warning(
                    "Groq could not process the request. "
                    "Using the built-in parser instead. "
                    f"Details: {groq_error}"
                )

        # Step 3: Let the user inspect the final requirements.
        with st.expander("View interpreted rental requirements"):
            st.json(requirements)

        # Step 4: Retrieve listings using the selected data source.
        with st.spinner("Searching for rental properties..."):
            if use_demo:
                raw_df = demo_properties()
            else:
                raw_df = search_rentals(requirements)

        if raw_df.empty:
            st.warning(
                "No properties were returned. "
                "Try demo mode or change your search."
            )
            st.stop()

        # Step 5: Rank results using the existing ranking service.
        ranked = rank_properties(
            raw_df, requirements
        ).head(top_k).copy()

        if ranked.empty:
            st.warning(
                "No matching properties found. "
                "Try relaxing your requirements."
            )
            st.stop()

        # Step 6: Display results and metrics.
        st.success(f"Found {len(ranked)} matching properties.")

        m1, m2, m3, m4 = st.columns(4)

        m1.metric("Results", len(ranked))

        m2.metric(
            "Best match",
            f"{ranked['match_score'].max():.0f}%"
        )

        m3.metric(
            "Average rent",
            money(ranked["price"].mean())
            if "price" in ranked
            else "N/A",
        )

        m4.metric(
            "Source",
            "Demo" if use_demo else "RentCast"
        )

        for _, row in ranked.iterrows():
            show_property(row)

        # Step 7: Allow results to be downloaded.
        st.download_button(
            "⬇️ Download CSV",
            ranked.to_csv(index=False),
            file_name="rentlense_results.csv",
            mime="text/csv",
            use_container_width=True,
        )

    except RentCastError as exc:
        st.error(str(exc))

    
    except Exception as exc:
     st.error(f"Unexpected application error: {exc}")
     st.code(traceback.format_exc())